#!/usr/bin/env python3
"""Deployment-time fail-closed security contract for the public PWA runtime."""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runtime_security


def basic(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


def main() -> None:
    saved = {
        key: os.environ.get(key)
        for key in (
            "OWNER_BASIC_USER",
            "OWNER_BASIC_PASSWORD",
            "AI_BACKEND_PROXY_TOKEN",
        )
    }
    try:
        for key in saved:
            os.environ.pop(key, None)

        assert runtime_security.owner_auth_configured() is False
        assert runtime_security.owner_authorized(basic("x", "y")) is False
        assert runtime_security.backend_proxy_token() == ""

        os.environ["OWNER_BASIC_USER"] = "mehmet"
        os.environ["OWNER_BASIC_PASSWORD"] = "selftest-password"
        os.environ["AI_BACKEND_PROXY_TOKEN"] = "selftest-proxy-token"

        assert runtime_security.owner_auth_configured() is True
        assert runtime_security.owner_authorized(
            basic("mehmet", "selftest-password")
        ) is True
        assert runtime_security.owner_authorized(
            basic("mehmet", "wrong")
        ) is False
        assert runtime_security.backend_proxy_token() == "selftest-proxy-token"
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print("RUNTIME_SECURITY_SELFTEST=PASS")


if __name__ == "__main__":
    main()
