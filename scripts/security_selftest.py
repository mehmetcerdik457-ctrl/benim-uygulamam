#!/usr/bin/env python3
"""Deployment-time fail-closed security contract for the P1 backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server


def main() -> None:
    old = os.environ.pop("AI_BACKEND_PROXY_TOKEN", None)
    try:
        assert server.proxy_configured() is False
        assert server.proxy_authorized({}) is False

        os.environ["AI_BACKEND_PROXY_TOKEN"] = "selftest-proxy-token"
        assert server.proxy_configured() is True
        assert server.proxy_authorized(
            {"X-MEH-Proxy-Token": "selftest-proxy-token"}
        ) is True
        assert server.proxy_authorized(
            {"X-MEH-Proxy-Token": "wrong-token"}
        ) is False
    finally:
        if old is None:
            os.environ.pop("AI_BACKEND_PROXY_TOKEN", None)
        else:
            os.environ["AI_BACKEND_PROXY_TOKEN"] = old

    print("BACKEND_SECURITY_SELFTEST=PASS")


if __name__ == "__main__":
    main()
