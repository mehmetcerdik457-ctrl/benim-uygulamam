"""Read-only runner-host acceptance for the *opt-in* restricted demo gateway.

Checks Docker network membership and real HTTP denial. Never verifies Owner
hardware, target phone or production ingress. Sanitized constant-only output.
"""
import json
import socket
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

COMPOSE = ("docker", "compose", "-f", "compose.omega.yml", "-f", "compose.omega-host.yml")
HOST = "http://127.0.0.1:18081"


def _run(args, runner=subprocess.run):
    try:
        r = runner(args, text=True, capture_output=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 and len(r.stdout) <= 16384 else None


def _container(service, runner=subprocess.run):
    cid = _run((*COMPOSE, "ps", "-q", service), runner=runner)
    if not cid or len(cid.splitlines()) != 1:
        return None
    p = _run(("docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", cid), runner=runner)
    n = _run(("docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", cid), runner=runner)
    try:
        ports, networks = json.loads(p), json.loads(n)
        if not isinstance(ports, dict) or not isinstance(networks, dict):
            return None
        internal_flags = {}
        for name in networks:
            raw = _run(("docker", "network", "inspect", "--format",
                        "{{json .Internal}}", name), runner=runner)
            if raw not in ("true", "false"):
                return None
            internal_flags[name] = raw == "true"
        return {"ports": ports, "internal": sorted(internal_flags.values())}
    except (ValueError, TypeError, AttributeError):
        return None


def _request(path, *, method="GET", body=None, opener=None):
    opener = opener or build_opener(ProxyHandler({})).open
    req = Request(HOST + path, method=method, data=body,
                  headers={"Content-Type": "application/json"})
    try:
        with opener(req, timeout=4) as r:
            return r.status, r.read(8193)
    except HTTPError as e:
        return e.code, e.read(8193)


def diagnose(*, runner=subprocess.run, opener=None, connector=socket.create_connection):
    api = _container("api", runner=runner)
    db = _container("db", runner=runner)
    gw = _container("host-gateway", runner=runner)
    if not (api and db and gw):
        return "BLOCKED_INSPECT_UNAVAILABLE"
    # Database and app must be internal-only and not host-published.
    if api["internal"] != [True] or db["internal"] != [True]:
        return "UNSAFE_PRIVATE_NETWORK"
    if any(v for v in api["ports"].values()) or any(v for v in db["ports"].values()):
        return "UNSAFE_DIRECT_HOST_MAPPING"
    # Gateway deliberately spans two separate networks; only gateway is reachable.
    if gw["internal"] != [False, True]:
        return "UNSAFE_GATEWAY_NETWORK"
    bindings = gw["ports"].get("8080/tcp")
    if (not isinstance(bindings, list) or len(bindings) != 1
        or bindings[0].get("HostIp") != "127.0.0.1"
        or str(bindings[0].get("HostPort")) != "18081"
        or any(value for port, value in gw["ports"].items() if port != "8080/tcp")):
        return "UNSAFE_GATEWAY_BINDING"
    try:
        with connector(("127.0.0.1", 18081), timeout=4):
            pass
    except OSError:
        return "BLOCKED_HOST_TCP"
    try:
        status, payload = _request("/api/health", opener=opener)
        if status != 200 or json.loads(payload) != {"mode":"mock","production_ready":False}:
            return "UNSAFE_HEALTH_RESPONSE"
        status, payload = _request("/api/execute", method="POST",body=b"{}", opener=opener)
        if status != 403 or json.loads(payload).get("error") != "EXECUTION_DENIED":
            return "UNSAFE_EXECUTION_NOT_DENIED"
        status, _ = _request("/api/chat", method="POST",body=b"{}", opener=opener)
        if status != 403:
            return "UNSAFE_CHAT_EXPOSED"
        status, _ = _request("/api/models", opener=opener)
        if status != 404:
            return "UNSAFE_MODELS_EXPOSED"
    except (URLError, OSError, ValueError, TypeError, TimeoutError, KeyError):
        return "BLOCKED_HTTP_NOT_VERIFIED"
    return "PASS_RUNNER_DEMO_GATEWAY_ONLY_NOT_OWNER"


def main():
    result = diagnose()
    print("OMEGA_HOST_GATEWAY_VERDICT=" + result)
    return 0 if result == "PASS_RUNNER_DEMO_GATEWAY_ONLY_NOT_OWNER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
