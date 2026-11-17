#!/usr/bin/env python3
"""Explicit, bounded server-only model proof using the existing vault environment.

Run with --live inside the authorized backend. This is not a phone or owner
enrollment test. No secret value, private prompt, or provider error body is logged.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from omega import gateway
from omega_bridge import RuntimeProvider


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    evidence = {"event": "omega_provider_acceptance", "provider": "openai",
                "provider_request_made": False, "owner_device_acceptance": False}
    if args != ["--live"]:
        print(json.dumps({**evidence, "status": "NOT_RUN", "error": "EXPLICIT_LIVE_FLAG_REQUIRED"}))
        return 2
    provider = RuntimeProvider()
    try:
        if not provider.configured():
            raise gateway.Denied("PROVIDER_NOT_CONFIGURED", 503)
        selected = provider.candidates()[0]
        evidence["requested_model"] = selected
        evidence["provider_request_made"] = True
        text, actual, latency = provider.reply(selected, "Yalnızca Merhaba yaz.", probe=True)
        evidence.update(status="VERIFIED_PROVIDER_RESPONSE", provider_model=actual,
            latency_ms=latency, response_text=text,
            response_text_sha256=hashlib.sha256(text.encode()).hexdigest())
        print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        return 0
    except gateway.Denied as error:
        print(json.dumps({**evidence, "status": "DENIED", "error": error.code}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({**evidence, "status": "DENIED", "error": "PROVIDER_ACCEPTANCE_FAILED"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
