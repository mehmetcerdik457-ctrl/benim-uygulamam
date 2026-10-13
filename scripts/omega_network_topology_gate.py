"""OMEGA CI-only Compose topology analysis; never changes networks or grants access.

This is a STATIC policy check over *rendered* docker compose config JSON.
It does NOT establish host port publication, HTTP reachability or owner access.
A healthy container on an internal bridge is not proof of a host listener.
"""
import argparse
import json
import sys
from typing import Any


def _networks(service: Any) -> set[str] | None:
    if not isinstance(service, dict):
        return None
    values = service.get("networks")
    if isinstance(values, list) and all(type(x) is str for x in values):
        return set(values)
    if isinstance(values, dict) and all(type(x) is str for x in values):
        return set(values)
    return None


def _port(port: Any) -> bool:
    if isinstance(port, str):
        # Some Compose versions expose the compact syntax.
        return port == "127.0.0.1:18080:8000"
    if not isinstance(port, dict):
        return False
    return (
        port.get("host_ip") == "127.0.0.1"
        and type(port.get("target")) is int and port["target"] == 8000
        and str(port.get("published")) == "18080"
        and port.get("protocol", "tcp") == "tcp"
    )


def evaluate(config: object) -> dict[str, str | bool]:
    """Fixed-vocabulary verdict; never print supplied config or environment."""
    base: dict[str, str | bool] = {
        "topology": "DENIED",
        "host_acceptance": "BLOCKED_NOT_ACCEPTED",
        "production_ready": False,
        "cause": "UNVERIFIED_NETWORK_POLICY",
    }
    if not isinstance(config, dict):
        return {**base, "cause": "COMPOSE_JSON_UNAVAILABLE_OR_INVALID"}
    services = config.get("services")
    networks = config.get("networks")
    if not isinstance(services, dict) or not isinstance(networks, dict):
        return {**base, "cause": "RENDERED_SERVICE_OR_NETWORK_SECTION_MISSING"}
    if not {"api", "db"}.issubset(services) or not set(services).issubset({"api", "db", "tests"}):
        return {**base, "cause": "REQUIRED_SERVICE_MISSING"}
    isolated = networks.get("isolated_demo")
    if not isinstance(isolated, dict) or isolated.get("internal") is not True:
        return {**base, "cause": "INTERNAL_NETWORK_REQUIRED"}
    for name in ("api", "db", "tests"):
        if name not in services:
            continue  # Compose excludes inactive integration profiles.
        service = services[name]
        if _networks(service) != {"isolated_demo"}:
            return {**base, "cause": "UNEXPECTED_NETWORK_ATTACHMENT"}
        if "network_mode" in service or "extra_hosts" in service:
            return {**base, "cause": "EXTRA_NETWORK_PATH_DENIED"}
        if name != "api" and service.get("ports"):
            return {**base, "cause": "NON_API_PORT_PUBLISHED"}
    api = services["api"]
    if (not isinstance(api, dict) or api.get("read_only") is not True
            or api.get("cap_drop") != ["ALL"]
            or "no-new-privileges:true" not in api.get("security_opt", [])):
        return {**base, "cause": "API_HARDENING_MISSING"}
    ports = api.get("ports")
    if not isinstance(ports, list) or len(ports) != 1 or not _port(ports[0]):
        return {**base, "cause": "UNSAFE_OR_MISSING_API_BINDING"}
    return {
        "topology": "PASS_INTERNAL_AND_LOOPBACK_REQUEST_ONLY",
        "host_acceptance": "BLOCKED_NOT_ACCEPTED",
        "production_ready": False,
        "cause": "EFFECTIVE_DOCKER_PUBLISH_AND_HTTP_UNVERIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdin", action="store_true", required=True)
    parser.parse_args(argv)
    # Max input 1MB, avoid shell environment/secret output even on errors.
    raw = sys.stdin.read(1024 * 1024 + 1)
    try:
        if len(raw) > 1024 * 1024:
            raise ValueError("oversized")
        data = json.loads(raw)
    except (ValueError, TypeError):
        data = None
    result = evaluate(data)
    for key in ("topology", "host_acceptance", "production_ready", "cause"):
        print("OMEGA_NETWORK_" + key.upper() + "=" + str(result[key]).upper())
    return 0 if result["topology"] == "PASS_INTERNAL_AND_LOOPBACK_REQUEST_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
