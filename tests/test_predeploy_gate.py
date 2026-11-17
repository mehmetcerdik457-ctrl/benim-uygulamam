"""Deployment gate diagnostics must identify failure without printing secrets."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("predeploy_gate", ROOT / "scripts" / "predeploy_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def backend(**overrides):
    values = dict(
        OPENAI_URL="https://api.openai.com/v1/responses",
        configured=lambda: True,
        proxy_configured=lambda: True,
        owner_p256=SimpleNamespace(configured=lambda: True),
        DEFAULT_MODEL="operator-selected-model",
        MAX_OUTPUT_TOKENS=2048,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture(autouse=True)
def clean_numeric_config(monkeypatch):
    for name in gate.NUMERIC_FIELDS:
        monkeypatch.delenv(name, raising=False)


def test_all_existing_gate_checks_remain_mandatory():
    commands = []
    report = gate.run_gate(backend_loader=backend, run_command=lambda command: commands.append(command) or True)
    assert report["status"] == gate.PASS
    assert report["provider_request_made"] is False
    assert len(commands) == 2
    assert commands[0][1:] == ["-m", "compileall", "-q", "backend", "tests", "scripts"]
    assert commands[1][1:] == ["scripts/security_selftest.py"]
    assert all(value == "PASS" for value in report["checks"].values())


@pytest.mark.parametrize("change,expected", [
    ({"OPENAI_URL": "https://wrong.invalid"}, "openai_endpoint_is_fixed"),
    ({"configured": lambda: False}, "provider_credentials_present"),
    ({"proxy_configured": lambda: False}, "proxy_auth_present"),
    ({"owner_p256": SimpleNamespace(configured=lambda: False)}, "owner_p256_config_present"),
    ({"DEFAULT_MODEL": ""}, "selected_model_present"),
    ({"MAX_OUTPUT_TOKENS": 0}, "output_token_limit_positive_integer"),
    ({"MAX_OUTPUT_TOKENS": True}, "output_token_limit_positive_integer"),
])
def test_named_failed_configuration_predicate_blocks_deployment(change, expected):
    report = gate.run_gate(backend_loader=lambda: backend(**change), run_command=lambda _: True)
    assert report["status"] == "DENIED"
    assert report["checks"][expected] == "FAIL"
    assert report["checks"]["security_selftest"] == "PASS"


@pytest.mark.parametrize("name", list(gate.NUMERIC_FIELDS))
def test_numeric_import_failure_is_named_without_echoing_value(monkeypatch, name):
    private = "private-config-value-not-for-output"
    monkeypatch.setenv(name, private)
    called = []
    report = gate.run_gate(backend_loader=lambda: called.append(True), run_command=lambda _: True)
    assert report["status"] == "DENIED"
    assert report["checks"]["parse_" + name] == "FAIL"
    assert report["checks"]["backend_import"] == "NOT_RUN"
    assert not called
    assert private not in json.dumps(report)


def test_import_exception_and_import_output_are_sanitized(capsys):
    private = "private-owner-or-provider-value"
    def loader():
        print(private)
        raise RuntimeError(private)
    report = gate.run_gate(backend_loader=loader, run_command=lambda _: True)
    assert report["status"] == "DENIED"
    assert report["checks"]["backend_import"] == "FAIL"
    assert private not in json.dumps(report) + capsys.readouterr().out


@pytest.mark.parametrize("failure", ["compile_source", "security_selftest"])
def test_failed_subprocess_cannot_be_bypassed(failure):
    def execute(command):
        return ("compileall" in command) != (failure == "compile_source")
    report = gate.run_gate(backend_loader=backend, run_command=execute)
    assert report["status"] == "DENIED"
    assert report["checks"][failure] == "FAIL"


def test_subprocess_timeout_or_exception_is_sanitized():
    private = "private-subprocess-output"
    def execute(command):
        raise subprocess.TimeoutExpired(command, 60, output=private, stderr=private)
    report = gate.run_gate(backend_loader=backend, run_command=execute)
    assert report["status"] == "DENIED"
    assert report["checks"]["compile_source"] == "FAIL"
    assert report["checks"]["security_selftest"] == "FAIL"
    assert private not in json.dumps(report)


def test_unexpected_predicate_error_is_denied_without_detail():
    def failure():
        raise RuntimeError("private-configuration")
    report = gate.run_gate(backend_loader=lambda: backend(configured=failure), run_command=lambda _: True)
    assert report["checks"]["provider_credentials_present"] == "FAIL"
    assert report["status"] == "DENIED"
    assert "private-configuration" not in json.dumps(report)


def test_no_cli_skip_flags_are_accepted(capsys):
    assert gate.main(["--skip-security-selftest"]) == 2
    output = capsys.readouterr().out
    assert '"arguments":"FAIL"' in output
    assert "OMEGA_PREDEPLOY_OFFLINE=DENIED" in output


def test_real_cli_gate_uses_only_synthetic_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-provider-value-not-a-real-key")
    monkeypatch.setenv("AI_BACKEND_PROXY_TOKEN", "synthetic-proxy-value-only")
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", "synthetic-presence-only-not-an-enrolled-key")
    monkeypatch.setenv("OPENAI_MODEL", "operator-selected-test-model")
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "predeploy_gate.py")],
        cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0
    first = json.loads(result.stdout.splitlines()[0])
    assert first["status"] == gate.PASS
    assert first["provider_request_made"] is False
    for private in ["synthetic-provider-value-not-a-real-key", "synthetic-proxy-value-only",
                    "synthetic-presence-only-not-an-enrolled-key", "operator-selected-test-model"]:
        assert private not in result.stdout + result.stderr
