#!/usr/bin/env python3
"""OMEGA P1 provider preflight: offline by default, never a deployment-time live request.

LIVE mode makes one approved billable request only outside CI/hosted Railway.
It is never part of Railway pre-deploy; approval and model identity are explicit.
No credentials, prompts, provider replies, or exception messages are printed.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

EXPECTED = "MEHMET_LIVE_OK"
PROMPT = "Reply exactly MEHMET_LIVE_OK"
MAX_PROBE_OUTPUT_TOKENS = 16


def preflight(backend: object) -> bool:
    """Validate configuration shape without using a model or reading secret values."""
    models = getattr(backend, "ALLOWED_MODELS", ())
    selected = getattr(backend, "DEFAULT_MODEL", None)
    return (
        getattr(backend, "OPENAI_URL", None) == "https://api.openai.com/v1/responses"
        and callable(getattr(backend, "configured", None))
        and bool(backend.configured())
        and callable(getattr(backend, "proxy_configured", None))
        and bool(backend.proxy_configured())
        and type(models) is tuple
        and bool(models)
        and type(selected) is str
        and bool(selected)
        and selected in models
        and type(getattr(backend, "MAX_OUTPUT_TOKENS", None)) is int
        and backend.MAX_OUTPUT_TOKENS > 0
    )


def exact_reply_ok(reply: object) -> bool:
    return type(reply) is str and reply.strip() == EXPECTED


def execute(mode: str, backend: object, environ: dict[str, str]) -> int:
    """Return status: 0 pass, 1 mismatch/provider error, 2 denied."""
    try:
        valid = preflight(backend)
    except Exception:
        valid = False
    if not valid:
        print("OMEGA_PROVIDER_PREFLIGHT=CONFIGURATION_DENIED")
        return 2
    if mode == "offline":
        print("OMEGA_PROVIDER_PREFLIGHT=PASS_OFFLINE_NO_MODEL_REQUEST")
        return 0
    if mode != "live":
        print("OMEGA_PROVIDER_SMOKE=MODE_DENIED")
        return 2
    if (environ.get("OMEGA_SINGLE_PROVIDER_PROBE_APPROVED") != "YES"
            or environ.get("OMEGA_SINGLE_PROVIDER_PROBE_MODEL") != backend.DEFAULT_MODEL):
        print("OMEGA_PROVIDER_SMOKE=OWNER_APPROVAL_OR_MODEL_DENIED")
        return 2
    # Automation must never be able to spend money even if an approval flag
    # is accidentally present. Production Railway must use --mode offline.
    if any(environ.get(name) for name in (
            "CI", "GITHUB_ACTIONS", "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_SERVICE_ID", "RAILWAY_PROJECT_ID")):
        print("OMEGA_PROVIDER_SMOKE=AUTOMATED_OR_HOSTED_RUNTIME_DENIED")
        return 2
    # The backend explicitly supports a request-local limit; never alter a
    # shared module-level default in a concurrent server.
    if not callable(getattr(backend, "call_openai", None)):
        print("OMEGA_PROVIDER_SMOKE=SAFE_LIVE_ADAPTER_NOT_IMPLEMENTED")
        return 2
    try:
        reply, model = backend.call_openai(
            PROMPT, [], max_output_tokens=MAX_PROBE_OUTPUT_TOKENS,
        )
    except Exception:
        print("OMEGA_PROVIDER_SMOKE=UPSTREAM_FAILED")
        return 1
    if model != backend.DEFAULT_MODEL or not exact_reply_ok(reply):
        print("OMEGA_PROVIDER_SMOKE=RESPONSE_MISMATCH")
        return 1
    print("OMEGA_PROVIDER_SMOKE=PASS_SINGLE_LIVE_REQUEST")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    args = parser.parse_args(argv)
    try:
        import server
    except Exception:
        print("OMEGA_PROVIDER_PREFLIGHT=IMPORT_DENIED")
        return 2
    return execute(args.mode, server, os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
