"""Read-only, fail-closed audit of Docker's requested vs effective OMEGA port.

A Compose ports declaration is not runtime host publication. This script does
not change Compose, host networking, Docker services, or firewall rules.
Only fixed-status fields are logged (no IDs, errors, secrets, or raw inspect).
Runner checks do not prove owner-device or HTTP acceptance.
"""
import json
import re
import subprocess

EXPECTED_PORT = "8080/tcp"
EXPECTED_BINDING = {"HostIp": "127.0.0.1", "HostPort": "18080"}
COMPOSE = ("docker", "compose", "-f", "compose.omega.yml")


def _read(args, runner=subprocess.run):
    try:
        result = runner(list(args), capture_output=True, text=True,
                        timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not isinstance(result.stdout, str):
        return None
    return result.stdout.strip()[:12000]


def _json(args, runner):
    raw = _read(args, runner)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _binding(table):
    if not isinstance(table, dict):
        return "UNVERIFIED"
    # Docker uses only null or [] for an exposed-but-unpublished port.
    # False, 0, "", {} and other malformed extra mappings must fail closed.
    if any(port != EXPECTED_PORT and bindings is not None
           and not (type(bindings) is list and len(bindings) == 0)
           for port, bindings in table.items()):
        return "UNSAFE"
    published = table.get(EXPECTED_PORT)
    if published is None or published == []:
        return "MISSING"
    if (isinstance(published, list) and len(published) == 1
            and isinstance(published[0], dict)
            and published[0] == EXPECTED_BINDING):
        return "LOOPBACK_ONLY"
    return "UNSAFE"


def _networks(table, runner):
    # A suffix-matching name is not an authorized Compose network.
    expected = {"omega-mvi-demo_isolated_demo": True,
                "omega-mvi-demo_loopback_ingress": False}
    if not isinstance(table, dict):
        return "UNVERIFIED"
    if set(table) != set(expected):
        return "UNSAFE"
    states = {}
    for name in expected:
        internal = _json(["docker", "network", "inspect", "--format",
                          "{{json .Internal}}", name], runner)
        if type(internal) is not bool:
            return "UNVERIFIED"
        states[name] = internal
    return "SEGMENTED_INGRESS" if states == expected else "UNSAFE"


def _private_services_isolated(runner):
    """Require live API and DB to have only the internal network, no host ports."""
    for service in ("api", "db"):
        cid = _read((*COMPOSE, "ps", "-q", service), runner)
        if not cid or len(cid.splitlines()) != 1:
            return "UNVERIFIED"
        networks = _json(["docker", "inspect", "--format",
                          "{{json .NetworkSettings.Networks}}", cid], runner)
        ports = _json(["docker", "inspect", "--format",
                       "{{json .NetworkSettings.Ports}}", cid], runner)
        if not isinstance(networks, dict) or not isinstance(ports, dict):
            return "UNVERIFIED"
        if set(networks) != {"omega-mvi-demo_isolated_demo"}:
            return "UNSAFE"
        if any(binding is not None
               and not (type(binding) is list and len(binding) == 0)
               for binding in ports.values()):
            return "UNSAFE"
    return "ISOLATED"


def audit(runner=subprocess.run):
    cid = _read((*COMPOSE, "ps", "-q", "ingress"), runner)
    result = dict(requested="UNVERIFIED", effective="UNVERIFIED",
                  compose_port="UNVERIFIED", network="UNVERIFIED",
                  engine_version="UNVERIFIED", cause="INCOMPLETE_EVIDENCE",
                  verdict="BLOCKED_NOT_ACCEPTED")
    version = _read(["docker", "version", "--format", "{{.Server.Version}}"], runner)
    if version and re.fullmatch(r"\d+(?:\.\d+){1,3}(?:[-+][A-Za-z0-9_.-]+)?", version):
        result["engine_version"] = version
    if not cid or len(cid.splitlines()) != 1:
        result["cause"] = "API_CONTAINER_NOT_IDENTIFIED"
        return result
    requested = _json(["docker", "inspect", "--format",
                       "{{json .HostConfig.PortBindings}}", cid], runner)
    effective = _json(["docker", "inspect", "--format",
                       "{{json .NetworkSettings.Ports}}", cid], runner)
    attached = _json(["docker", "inspect", "--format",
                      "{{json .NetworkSettings.Networks}}", cid], runner)
    result["requested"] = _binding(requested)
    result["effective"] = _binding(effective)
    result["network"] = _networks(attached, runner)
    private_services = _private_services_isolated(runner)
    if private_services == "UNSAFE":
        result["network"] = "UNSAFE"
    elif private_services != "ISOLATED" and result["network"] == "SEGMENTED_INGRESS":
        result["network"] = "UNVERIFIED"
    compose_port = _read((*COMPOSE, "port", "ingress", "8080"), runner)
    if not compose_port:
        result["compose_port"] = "MISSING"
    elif compose_port == "127.0.0.1:18080":
        result["compose_port"] = "LOOPBACK_ONLY"
    else:
        result["compose_port"] = "UNSAFE"
    statuses = (result["requested"], result["effective"],
                result["compose_port"], result["network"])
    if "UNSAFE" in statuses:
        result["cause"] = "UNSAFE_DOCKER_NETWORK_OR_BINDING"
        result["verdict"] = "UNSAFE"
    elif (result["requested"] == "LOOPBACK_ONLY"
          and result["effective"] == "MISSING"
          and result["compose_port"] == "MISSING"
          and result["network"] == "SEGMENTED_INGRESS"):
        # Observed mismatch; underlying Docker decision path is not proven.
        result["cause"] = "DOCKER_REQUEST_ACCEPTED_BUT_PUBLICATION_NOT_EFFECTIVE"
    elif (result["requested"] == "LOOPBACK_ONLY"
          and result["effective"] == "LOOPBACK_ONLY"
          and result["compose_port"] == "LOOPBACK_ONLY"
          and result["network"] == "SEGMENTED_INGRESS"):
        result["cause"] = "DOCKER_MAPPING_PRESENT_HTTP_NOT_YET_CHECKED"
        result["verdict"] = "PORT_CONTRACT_PASS_NOT_HTTP_OR_OWNER"
    return result


def main():
    evidence = audit()
    for key in ("engine_version", "requested", "effective", "compose_port",
                "network", "cause", "verdict"):
        print(f"OMEGA_DOCKER_PORT_{key.upper()}={evidence[key]}")
    if evidence["verdict"] == "UNSAFE":
        return 1
    if evidence["verdict"] != "PORT_CONTRACT_PASS_NOT_HTTP_OR_OWNER":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
