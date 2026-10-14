"""Disposable A/B proof of Docker internal-network port publication semantics.

A/B containers are independent, static Python stdlib HTTP mocks:
- same image, container command, loopback-only random host port request
- sole test variable: user-defined bridge network internal=true versus false
No OMEGA service joins the comparison networks, no real data or credentials.
Both mock containers, then both experiment-only networks, are always removed.
No raw Docker CLI output, IDs, random ports or exceptions are printed.

This is a CI-only *diagnostic control*, never an owner/production acceptance.
"""
import argparse
import json
import os
import re
import secrets
import subprocess

# Use the immutable image already built for the synthetic CI Compose API.
# No credentials/environment from that service are inherited by the mock.
IMAGE = "LOCAL_COMPOSE_BUILD_ONLY"
IN_CONTAINER_PORT = "8000/tcp"
_TAG = "omega-ci-netctrl-"
_PORT_REGEX = re.compile(r"127\.0\.0\.1:(\d{1,5})\Z")


def _call(args, runner=subprocess.run, timeout=20):
    try:
        response = runner(list(args), capture_output=True, text=True,
                          check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if response.returncode != 0 or not isinstance(response.stdout, str):
        return None
    return response.stdout.strip()[:8192]


def mapping(requested, effective, cli_port):
    """Compare both inspect views AND docker port; return fixed status only."""
    if not isinstance(requested, dict) or not isinstance(effective, dict):
        return "UNVERIFIED"
    if set(requested) != {IN_CONTAINER_PORT}:
        return "UNSAFE"
    bindings = requested.get(IN_CONTAINER_PORT)
    if not isinstance(bindings, list) or len(bindings) != 1:
        return "UNSAFE"
    if bindings[0] != {"HostIp": "127.0.0.1", "HostPort": ""}:
        return "UNSAFE"
    if any(k != IN_CONTAINER_PORT and v for k, v in effective.items()):
        return "UNSAFE"
    got = effective.get(IN_CONTAINER_PORT)
    if got is None:
        return "MISSING" if cli_port is None else "UNSAFE"
    if not isinstance(got, list) or len(got) != 1 or not isinstance(got[0], dict):
        return "UNSAFE"
    item = got[0]
    if item.get("HostIp") != "127.0.0.1" or not _PORT_REGEX.fullmatch(
            "127.0.0.1:" + str(item.get("HostPort", ""))):
        return "UNSAFE"
    port = int(item["HostPort"])
    if port < 1024 or port > 65535:
        return "UNSAFE"
    return "LOOPBACK_ONLY" if cli_port == "127.0.0.1:" + str(port) else "UNSAFE"


def classify(internal, normal):
    if "UNSAFE" in (internal, normal):
        return "UNSAFE_BINDING_IN_CONTROL"
    if internal == "MISSING" and normal == "LOOPBACK_ONLY":
        return "REPRODUCED_INTERNAL_ONLY_PORT_OMISSION"
    if internal == "LOOPBACK_ONLY" and normal == "LOOPBACK_ONLY":
        return "NOT_REPRODUCED_BOTH_PUBLISHED"
    return "BLOCKED_INCONCLUSIVE"


def _inspect(name, runner):
    args = ["docker", "inspect", "--format",
            "{{json .HostConfig.PortBindings}}", name]
    raw_requested = _call(args, runner)
    raw_effective = _call(
        ["docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", name],
        runner)
    raw_port = _call(["docker", "port", name, IN_CONTAINER_PORT], runner)
    try:
        requested = json.loads(raw_requested) if raw_requested is not None else None
        effective = json.loads(raw_effective) if raw_effective is not None else None
    except (ValueError, TypeError):
        return "UNVERIFIED"
    return mapping(requested, effective, raw_port)


def _remove(name, runner):
    _call(["docker", "rm", "--force", name], runner, timeout=12)


def _remove_network(name, runner):
    _call(["docker", "network", "rm", name], runner, timeout=12)


def _probe(runner):
    """Runner returns subprocess compatible results; silent, bounded cleanup."""
    run_id = secrets.token_hex(6)
    names = {"internal": _TAG + run_id + "-int",
             "normal": _TAG + run_id + "-norm"}
    containers = {"internal": _TAG + run_id + "-a",
                  "normal": _TAG + run_id + "-b"}
    result = {"internal": "UNVERIFIED", "normal": "UNVERIFIED",
              "stage": "PRECHECK", "verdict": "BLOCKED_INCONCLUSIVE"}
    created_nets = []
    created_containers = []
    try:
        image_id = _call(["docker", "compose", "-f", "compose.omega.yml",
                          "images", "--quiet", "api"], runner)
        if not image_id or not re.fullmatch(
                r"(?:sha256:)?[0-9a-f]{12,64}", image_id):
            result["stage"] = "LOCAL_BUILT_IMAGE_UNAVAILABLE"
            return result  # No image pulls or external downloads.
        result["stage"] = "IMAGE_READY"
        for case in ("internal", "normal"):
            network = names[case]
            args = ["docker", "network", "create", "--driver", "bridge",
                    "--label", "omega.ci.disposable=network-control"]
            if case == "internal":
                args.append("--internal")
            if _call([*args, network], runner) is None:
                result["stage"] = "NETWORK_CREATE_FAILED_" + case.upper()
                return result
            created_nets.append(network)
        for case in ("internal", "normal"):
            name = containers[case]
            cmd = ["docker", "run", "--detach", "--rm", "--name", name,
                   "--network", names[case], "--user", "65534:65534",
                   "--read-only", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges:true",
                   "--publish", "127.0.0.1::8000",
                   image_id, "python", "-m", "http.server", "8000",
                   "--bind", "0.0.0.0", "--directory", "/tmp"]
            # Track the random name before starting, so a partially started
            # disposable container also gets removed after a CLI error.
            created_containers.append(name)
            if _call(cmd, runner, timeout=30) is None:
                result["stage"] = "MOCK_CONTAINER_START_FAILED_" + case.upper()
                return result
        result["stage"] = "BOTH_MOCKS_STARTED"
        for case in ("internal", "normal"):
            result[case] = _inspect(containers[case], runner)
        result["stage"] = "BOTH_PORTS_INSPECTED"
        result["verdict"] = classify(result["internal"], result["normal"])
        return result
    finally:
        for name in reversed(created_containers):
            _remove(name, runner)
        for name in reversed(created_nets):
            _remove_network(name, runner)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-disposable", action="store_true")
    args = parser.parse_args(argv)
    if not args.ci_disposable or os.environ.get("GITHUB_ACTIONS") != "true":
        print("OMEGA_NETWORK_CONTROL=DISABLED_OUTSIDE_EXPLICIT_CI")
        return 2
    outcome = _probe(subprocess.run)
    for k in ("stage", "internal", "normal", "verdict"):
        print("OMEGA_NETWORK_CONTROL_" + k.upper() + "=" + outcome[k])
    if outcome["verdict"] == "UNSAFE_BINDING_IN_CONTROL":
        return 1
    return 0 if outcome["verdict"] == "REPRODUCED_INTERNAL_ONLY_PORT_OMISSION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
