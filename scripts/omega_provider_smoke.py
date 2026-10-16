#!/usr/bin/env python3
"""OMEGA P1 provider preflight: offline by default, never a deployment-time live request.

LIVE mode is disabled until a per-request bounded provider adapter is implemented.
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
    # This is a standalone, manually approved test, NEVER a deploy/CI step.
    # Do not mutate a shared module-level token limit: threaded callers may race.
    # This inherited backend does not accept a per-request output cap.
    # Refuse LIVE requests instead of falsely claiming that changing its global
    # module attribute constrains other concurrently executing provider calls.
    print("OMEGA_PROVIDER_SMOKE=SAFE_LIVE_ADAPTER_NOT_IMPLEMENTED")
    return 2
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
