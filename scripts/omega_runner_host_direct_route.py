"""Read-only runner-host -> Docker INTERNAL container-IP diagnostic.

Never validates owner machine; never modifies Docker networks or local firewall.
Allows only a single internal bridge endpoint with an RFC1918 IPv4 address
matching that Docker network's declared subnet. Does not print target IP,
container IDs, HTTP bodies, secret values, or exception messages.
"""
import ipaddress
import json
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from omega_runner_host_port_audit import COMPOSE, _json, _read

RFC1918 = tuple(ipaddress.ip_network(cidr) for cidr in
                ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def target_ip(runner=subprocess.run):
    cid = _read((*COMPOSE, "ps", "-q", "api"), runner)
    if not cid or len(cid.splitlines()) != 1:
        return None, "CONTAINER_UNKNOWN"
    networks = _json(["docker", "inspect", "--format",
                      "{{json .NetworkSettings.Networks}}", cid], runner)
    if not isinstance(networks, dict) or len(networks) != 1:
        return None, "NETWORK_SCOPE_UNVERIFIED"
    name, endpoint = next(iter(networks.items()))
    if not isinstance(name, str) or not isinstance(endpoint, dict):
        return None, "NETWORK_SCOPE_UNVERIFIED"
    internal = _json(["docker", "network", "inspect", "--format",
                      "{{json .Internal}}", name], runner)
    driver = _read(["docker", "network", "inspect", "--format",
                    "{{.Driver}}", name], runner)
    subnet_configs = _json(["docker", "network", "inspect", "--format",
                            "{{json .IPAM.Config}}", name], runner)
    if internal is not True or driver != "bridge":
        return None, "NETWORK_SCOPE_UNSAFE"
    try:
        ip = ipaddress.IPv4Address(endpoint.get("IPAddress"))
        if not any(ip in network for network in RFC1918):
            return None, "NETWORK_SCOPE_UNSAFE"
        # Fail closed on malformed IPAM entries and overly broad ranges.
        # An RFC1918 endpoint alone does NOT prove the underlying Docker
        # subnet is private (e.g., a reported 0.0.0.0/0 would also match it).
        if not isinstance(subnet_configs, list) or not subnet_configs:
            return None, "IPAM_UNVERIFIED"
        private_match = False
        for item in subnet_configs:
            if not isinstance(item, dict) or not isinstance(item.get("Subnet"), str):
                return None, "IPAM_UNVERIFIED"
            subnet = ipaddress.ip_network(item["Subnet"], strict=False)
            if isinstance(subnet, ipaddress.IPv4Network) and ip in subnet:
                if not any(subnet.subnet_of(private) for private in RFC1918):
                    return None, "NETWORK_SCOPE_UNSAFE"
                private_match = True
        if not private_match:
            return None, "IPAM_UNVERIFIED"
    except (ValueError, TypeError, AttributeError, ipaddress.AddressValueError):
        return None, "IPAM_UNVERIFIED"
    return str(ip), "SINGLE_INTERNAL_BRIDGE_RFC1918"


def _probe_http(ip, opener=None):
    # No HTTP proxy or authentication material is ever used.
    open_url = opener if opener is not None else build_opener(ProxyHandler({})).open
    base = "http://" + ip + ":8000"
    try:
        with open_url(base + "/api/health", timeout=4) as response:
            if getattr(response, "status", 200) != 200:
                return "HTTP_HEALTH_INVALID"
            doc = json.load(response)
        if (doc.get("mode") != "mock" or
                doc.get("production_ready") is not False or
                doc.get("external_api_enabled") is not False):
            return "HTTP_HEALTH_INVALID"
        request = Request(base + "/api/execute", data=b"{}",
                          method="POST",
                          headers={"Content-Type": "application/json"})
        try:
            with open_url(request, timeout=4):
                return "EXECUTION_UNEXPECTEDLY_ALLOWED"
        except HTTPError as error:
            return "PASS_HOST_TO_INTERNAL_ONLY" if error.code == 403 else "DENIAL_NOT_VERIFIED"
    except (OSError, URLError, TimeoutError, ValueError, TypeError, KeyError):
        return "HOST_TO_CONTAINER_BLOCKED"
    return "HOST_TO_CONTAINER_BLOCKED"


def diagnose(*, runner=subprocess.run, opener=None):
    ip, scope = target_ip(runner)
    if ip is None:
        return {"scope": scope, "http": "NOT_TESTED", "verdict": "BLOCKED_NOT_ACCEPTED"}
    status = _probe_http(ip, opener)
    return {"scope": scope, "http": status,
            "verdict": ("PASS_DIRECT_HOST_TO_INTERNAL_NOT_LOOPBACK_OR_OWNER"
                        if status == "PASS_HOST_TO_INTERNAL_ONLY"
                        else "BLOCKED_NOT_ACCEPTED")}


def main():
    report = diagnose()
    for key in ("scope", "http", "verdict"):
        print("OMEGA_DIRECT_HOST_" + key.upper() + "=" + report[key])
    return (0 if report["verdict"] == "PASS_DIRECT_HOST_TO_INTERNAL_NOT_LOOPBACK_OR_OWNER"
            else 2)


if __name__ == "__main__":
    raise SystemExit(main())
