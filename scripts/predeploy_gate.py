#!/usr/bin/env python3
"""Named, redacted checks for the existing fail-closed P1 deploy gate.

Never probes the model provider, prints configuration values, changes service
variables, enrolls an owner key, or starts a listener. Existing compile,
security-selftest and configuration checks all remain mandatory.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PASS = "PASS_CONFIG_ONLY_NO_MODEL_REQUEST"
NUMERIC_FIELDS = {
    "MAX_BODY_BYTES": (int, "65536"),
    "MAX_MESSAGE_CHARS": (int, "32000"),
    "MAX_OUTPUT_TOKENS": (int, "2048"),
    "UPSTREAM_TIMEOUT_SECONDS": (float, "45"),
    "RATE_LIMIT_PER_MINUTE": (int, "20"),
}
CONFIG_CHECKS = (
    "openai_endpoint_is_fixed", "provider_credentials_present",
    "proxy_auth_present", "owner_p256_config_present",
    "selected_model_present", "output_token_limit_positive_integer",
)


def _load_backend():
    backend_dir = str(ROOT / "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    specification = importlib.util.spec_from_file_location(
        "omega_predeploy_backend", ROOT / "backend" / "server.py")
    if specification is None or specification.loader is None:
        raise RuntimeError("backend source unavailable")
    backend = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(backend)
    return backend


def _run_command(command):
    result = subprocess.run(
        command, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
        timeout=60, check=False,
    )
    return result.returncode == 0


def _status(function):
    try:
        return "PASS" if function() else "FAIL"
    except Exception:
        return "FAIL"


def run_gate(*, backend_loader=None, run_command=None):
    """Return only fixed check names/statuses; no raw exceptions or subprocess I/O."""
    loader = _load_backend if backend_loader is None else backend_loader
    execute = _run_command if run_command is None else run_command
    checks = {"parse_" + name: "NOT_RUN" for name in NUMERIC_FIELDS}
    checks.update(dict.fromkeys(("backend_import", "compile_source", "security_selftest", *CONFIG_CHECKS), "NOT_RUN"))
    for name, (parser, default) in NUMERIC_FIELDS.items():
        try:
            parser(os.environ.get(name, default))
            checks["parse_" + name] = "PASS"
        except Exception:
            checks["parse_" + name] = "FAIL"

    if any(value == "FAIL" for value in checks.values()):
        return _report(checks)

    try:
        # An unexpected import print is not allowed to expose configuration.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            backend = loader()
        checks["backend_import"] = "PASS"
    except Exception:
        checks["backend_import"] = "FAIL"
        return _report(checks)

    checks["compile_source"] = _status(lambda: execute([
        sys.executable, "-m", "compileall", "-q", "backend", "tests", "scripts"]))
    checks["security_selftest"] = _status(lambda: execute([
        sys.executable, "scripts/security_selftest.py"]))

    predicates = {
        "openai_endpoint_is_fixed": lambda: backend.OPENAI_URL == "https://api.openai.com/v1/responses",
        "provider_credentials_present": lambda: backend.configured() is True,
        "proxy_auth_present": lambda: backend.proxy_configured() is True,
        "owner_p256_config_present": lambda: backend.owner_p256.configured() is True,
        "selected_model_present": lambda: isinstance(backend.DEFAULT_MODEL, str) and bool(backend.DEFAULT_MODEL.strip()),
        "output_token_limit_positive_integer": lambda: type(backend.MAX_OUTPUT_TOKENS) is int and backend.MAX_OUTPUT_TOKENS > 0,
    }
    for name, predicate in predicates.items():
        checks[name] = _status(predicate)
    return _report(checks)


def _report(checks):
    return {
        "event": "omega_predeploy_gate",
        "checks": checks,
        "status": PASS if checks and all(value == "PASS" for value in checks.values()) else "DENIED",
        "provider_request_made": False,
    }


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        report = _report({"arguments": "FAIL"})
    else:
        try:
            report = run_gate()
        except Exception:
            report = _report({"gate_execution": "FAIL"})
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    print("OMEGA_PREDEPLOY_OFFLINE=" + report["status"])
    return 0 if report["status"] == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
