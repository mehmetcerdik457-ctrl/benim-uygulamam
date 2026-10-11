"""Independent CI runner-host port diagnostic. NEVER validates owner's machine.

Uses read-only Docker inspect and localhost socket/HTTP checks. Does not print
container details, environment, credentials or error strings. Does not change
Compose network topology, publish additional ports or create Docker resources.
"""
import argparse
import json
import socket
import subprocess
from urllib.request import ProxyHandler, build_opener

from omega_probe_runner_loopback import BLOCKED, RUNNER_ONLY, probe

EXPECTED = "127.0.0.1:18080"
CONTAINER_PORT = "8000/tcp"


def _run(args, runner=subprocess.run):
    try:
        result = runner(args, text=True, capture_output=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()[:16000]


def _docker_evidence(runner=subprocess.run):
    cid = _run(["docker", "compose", "-f", "compose.omega.yml", "ps", "-q", "api"], runner)
    if not cid or len(cid.splitlines()) != 1:
        return "UNVERIFIED", "UNVERIFIED", "UNVERIFIED"

    ports_raw = _run(["docker", "inspect", "--format",
                      "{{json .NetworkSettings.Ports}}", cid], runner)
    networks_raw = _run(["docker", "inspect", "--format",
                         "{{json .NetworkSettings.Networks}}", cid], runner)
    binding = "UNVERIFIED"
    network = "UNVERIFIED"
    try:
        ports = json.loads(ports_raw) if ports_raw is not None else None
        published = ports.get(CONTAINER_PORT) if isinstance(ports, dict) else None
        if published is None:
            binding = "MISSING"
        elif isinstance(published, list) and published:
            if all(x.get("HostIp") == "127.0.0.1" and
                   str(x.get("HostPort")) == "18080" for x in published):
                binding = "LOOPBACK_ONLY"
            else:
                binding = "UNSAFE"
    except (ValueError, TypeError, AttributeError):
        pass

    try:
        networks = json.loads(networks_raw) if networks_raw is not None else None
        if isinstance(networks, dict) and networks and len(networks) <= 8:
            states = []
            for name in networks:
                raw = _run(["docker", "network", "inspect", "--format",
                            "{{json .Internal}}", name], runner)
                if raw is None:
                    states = []
                    break
                states.append(json.loads(raw))
            if states:
                network = "INTERNAL" if all(x is True for x in states) else "UNSAFE"
    except (ValueError, TypeError, AttributeError):
        pass

    healthy = _run(
        ["docker", "compose", "-f", "compose.omega.yml", "exec", "-T", "api",
         "python", "-c",
         "import json,urllib.request;"
         "x=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4));"
         "assert x['mode']=='mock' and x['production_ready'] is False;"
         "print('OK')"], runner)
    return binding, network, "PASS" if healthy == "OK" else "UNVERIFIED"


def _tcp_check(connector=socket.create_connection):
    try:
        with connector(("127.0.0.1", 18080), timeout=4):
            return "CONNECTED"
    except ConnectionRefusedError:
        return "REFUSED"
    except (TimeoutError, socket.timeout):
        return "TIMEOUT"
    except OSError:
        return "ERROR"


def diagnose(*, runner=subprocess.run, connector=socket.create_connection,
             opener=None):
    binding, network, inside = _docker_evidence(runner)
    tcp = _tcp_check(connector)
    http_status = "BLOCKED"
    if tcp == "CONNECTED":
        if opener is None:
            opener = build_opener(ProxyHandler({})).open
        try:
            outcome = probe(opener=opener)
            http_status = "PASS" if outcome == RUNNER_ONLY else "BLOCKED"
        except (AssertionError, ValueError, TypeError, KeyError, OSError):
            http_status = "UNSAFE"
    unsafe = binding == "UNSAFE" or network == "UNSAFE" or http_status == "UNSAFE"
    accepted = (not unsafe and binding == "LOOPBACK_ONLY"
                and network == "INTERNAL" and inside == "PASS"
                and tcp == "CONNECTED" and http_status == "PASS")
    if unsafe:
        verdict = "UNSAFE"
    elif accepted:
        verdict = "PASS_RUNNER_ONLY_NOT_OWNER"
    else:
        verdict = "BLOCKED_NOT_ACCEPTED"
    # Distinguish observed failure from unproven causal explanation.
    if binding == "MISSING":
        cause = "HOST_PORT_MAPPING_MISSING_UPSTREAM_CAUSE_UNKNOWN"
    elif tcp == "REFUSED":
        cause = "TCP_CONNECTION_REFUSED_ROOT_CAUSE_UNKNOWN"
    elif tcp == "TIMEOUT":
        cause = "TCP_TIMEOUT_ROOT_CAUSE_UNKNOWN"
    elif tcp == "ERROR":
        cause = "TCP_ERROR_ROOT_CAUSE_UNKNOWN"
    elif http_status == "BLOCKED":
        cause = "HTTP_BLOCKED_ROOT_CAUSE_UNKNOWN"
    elif unsafe:
        cause = "SECURITY_CONTRACT_UNSAFE"
    elif accepted:
        cause = "RUNNER_CONNECTIVITY_AND_DENIAL_VERIFIED"
    else:
        cause = "INCOMPLETE_EVIDENCE_ROOT_CAUSE_UNKNOWN"
    return {
        "binding": binding, "network": network, "container": inside,
        "tcp": tcp, "http": http_status, "verdict": verdict, "cause": cause,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-runner-host", action="store_true")
    opts = parser.parse_args(argv)
    report = diagnose()
    for key in ("binding", "network", "container", "tcp", "http", "cause", "verdict"):
        print("OMEGA_RUNNER_HOST_" + key.upper() + "=" + report[key])
    if report["verdict"] == "UNSAFE":
        return 1
    if opts.require_runner_host and report["verdict"] != "PASS_RUNNER_ONLY_NOT_OWNER":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
