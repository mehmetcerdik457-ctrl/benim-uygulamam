"""Offline Compose topology negative cases; no Docker or host mutations."""
from copy import deepcopy
from io import StringIO
import json
from unittest.mock import patch

from scripts.omega_network_topology_gate import evaluate, main


def topology():
    return {"networks": {"isolated_demo": {"internal": True}, "loopback_ingress": {"driver": "bridge"}},
            "services": {
                "api": {"networks": ["isolated_demo"], "read_only": True,
                        "cap_drop": ["ALL"],
                        "security_opt": ["no-new-privileges:true"],
                        },
                "ingress": {"networks": ["isolated_demo", "loopback_ingress"],
                            "user": "101:101",
                            "read_only": True, "cap_drop": ["ALL"],
                            "security_opt": ["no-new-privileges:true"],
                            "volumes": ["./omega_mvi/ingress/nginx.conf:/etc/nginx/nginx.conf:ro"],
                            "ports": [{"host_ip": "127.0.0.1", "target": 8080,
                                       "published": "18080", "protocol": "tcp"}]},
                "db": {"networks": ["isolated_demo"]},
                "tests": {"networks": ["isolated_demo"]}}}


def test_static_only_never_claims_runner_host_success():
    result = evaluate(topology())
    assert result["topology"] == "PASS_ISOLATED_API_AND_LOOPBACK_INGRESS_REQUEST_ONLY"
    assert result["host_acceptance"] == "BLOCKED_NOT_ACCEPTED"
    assert result["production_ready"] is False


def test_compact_port_equivalent_still_not_runtime_acceptance():
    config = topology()
    config["services"]["ingress"]["ports"] = ["127.0.0.1:18080:8080"]
    assert evaluate(config)["host_acceptance"] == "BLOCKED_NOT_ACCEPTED"


def test_raw_extra_external_network_does_not_bypass_policy():
    config = topology()
    config["networks"]["external"] = {"internal": False}
    config["services"]["api"]["networks"].append("external")
    assert evaluate(config)["topology"] == "DENIED"


def test_wildcard_or_extra_port_denied():
    config = topology()
    config["services"]["ingress"]["ports"][0]["host_ip"] = "0.0.0.0"
    assert evaluate(config)["topology"] == "DENIED"
    config = topology()
    config["services"]["ingress"]["ports"].append("0.0.0.0:8888:8000")
    assert evaluate(config)["topology"] == "DENIED"


def test_db_port_and_network_mode_denied():
    config = topology()
    config["services"]["db"]["ports"] = ["127.0.0.1:15432:5432"]
    assert evaluate(config)["topology"] == "DENIED"
    config = topology()
    config["services"]["api"]["network_mode"] = "host"
    assert evaluate(config)["topology"] == "DENIED"


def test_missing_hardening_or_external_network_never_passes():
    for part, value in [("read_only", False), ("cap_drop", []),
                        ("security_opt", [])]:
        config = topology()
        config["services"]["api"][part] = value
        assert evaluate(config)["topology"] == "DENIED"
    config = topology()
    config["networks"]["isolated_demo"]["internal"] = False
    assert evaluate(config)["topology"] == "DENIED"


def test_ingress_cannot_regress_to_privileged_user():
    config = topology()
    config["services"]["ingress"]["user"] = "0:0"
    assert evaluate(config)["topology"] == "DENIED"
    config = topology()
    del config["services"]["ingress"]["user"]
    assert evaluate(config)["topology"] == "DENIED"


def test_cli_outputs_only_fixed_codes_without_raw_input(capsys):
    config = topology()
    config["sensitive_unexpected_key"] = "UNSAFE_VALUE_DO_NOT_ECHO"
    with patch("sys.stdin", StringIO(json.dumps(config))):
        assert main(["--stdin"]) == 0
    output = capsys.readouterr().out
    assert "UNSAFE_VALUE_DO_NOT_ECHO" not in output
    assert "OMEGA_NETWORK_HOST_ACCEPTANCE=BLOCKED_NOT_ACCEPTED" in output
    with patch("sys.stdin", StringIO("{invalid }")):
        assert main(["--stdin"]) == 2


def test_inactive_integration_profile_is_optional_but_extra_service_denied():
    config = topology()
    del config["services"]["tests"]
    assert evaluate(config)["topology"] == "PASS_ISOLATED_API_AND_LOOPBACK_INGRESS_REQUEST_ONLY"
    config["services"]["unsafe-extra"] = {"networks": ["isolated_demo"]}
    assert evaluate(config)["topology"] == "DENIED"
