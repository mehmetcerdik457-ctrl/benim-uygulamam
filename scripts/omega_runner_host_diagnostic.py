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
CONTAINER_PORT = "8080/tcp"


def _run(args, runner=subprocess.run):
    try:
        result = runner(args, text=True, capture_output=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()[:16000]


def _private_services_isolated(runner):
    """Check the *running* API and DB, rather than only Compose declarations."""
    for service in ("api", "db"):
        cid = _run(["docker", "compose", "-f", "compose.omega.yml",
                    "ps", "-q", service], runner)
        if not cid or len(cid.splitlines()) != 1:
            return "UNVERIFIED"
        raw_nets = _run(["docker", "inspect", "--format",
                         "{{json .NetworkSettings.Networks}}", cid], runner)
        raw_ports = _run(["docker", "inspect", "--format",
                          "{{json .NetworkSettings.Ports}}", cid], runner)
        try:
            nets = json.loads(raw_nets) if raw_nets is not None else None
            ports = json.loads(raw_ports) if raw_ports is not None else None
        except (ValueError, TypeError):
            return "UNVERIFIED"
        if not isinstance(nets, dict) or not isinstance(ports, dict):
            return "UNVERIFIED"
        if set(nets) != {"omega-mvi-demo_isolated_demo"}:
            return "UNSAFE"
        if any(binding is not None
               and not (type(binding) is list and len(binding) == 0)
               for binding in ports.values()):
            return "UNSAFE"
    return "ISOLATED"


def _docker_evidence(runner=subprocess.run):
    cid = _run(["docker", "compose", "-f", "compose.omega.yml", "ps", "-q", "ingress"], runner)
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
        if isinstance(ports, dict):
            # Fail closed on extra published ports and duplicated/malformed binds.
            # Merely finding one allowed listener must never approve another one.
            extras = any(port != CONTAINER_PORT and bindings is not None
                         and not (type(bindings) is list and len(bindings) == 0)
                         for port, bindings in ports.items())
            published = ports.get(CONTAINER_PORT)
            if extras:
                binding = "UNSAFE"
            elif published is None or published == []:
                binding = "MISSING"
            elif (isinstance(published, list) and len(published) == 1
                  and isinstance(published[0], dict)
                  and published[0] == {"HostIp": "127.0.0.1",
                                       "HostPort": "18080"}):
                binding = "LOOPBACK_ONLY"
            else:
                binding = "UNSAFE"
    except (ValueError, TypeError, AttributeError):
        pass

    try:
        networks = json.loads(networks_raw) if networks_raw is not None else None
        if isinstance(networks, dict):
            # Verify the exact project-qualified network names, not suffixes.
            expected = {"omega-mvi-demo_isolated_demo": True,
                        "omega-mvi-demo_loopback_ingress": False}
            if set(networks) != set(expected):
                network = "UNSAFE"
            else:
                states = {}
                for name in expected:
                    raw = _run(["docker", "network", "inspect", "--format",
                                "{{json .Internal}}", name], runner)
                    if raw is None:
                        break
                    state = json.loads(raw)
                    if type(state) is not bool:
                        break
                    states[name] = state
                if len(states) == len(expected):
                    network = "SEGMENTED_INGRESS" if states == expected else "UNSAFE"
    except (ValueError, TypeError, AttributeError):
        pass

    private_services = _private_services_isolated(runner)
    if private_services == "UNSAFE":
        network = "UNSAFE"
    elif private_services != "ISOLATED" and network == "SEGMENTED_INGRESS":
        network = "UNVERIFIED"

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
                and network == "SEGMENTED_INGRESS" and inside == "PASS"
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
