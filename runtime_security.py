"""Runtime security helpers for the MEHMET personal PWA proxy."""
from __future__ import annotations

import base64
import hmac
import os


def owner_auth_configured() -> bool:
    return bool(
        os.getenv("OWNER_BASIC_USER", "").strip()
        and os.getenv("OWNER_BASIC_PASSWORD", "")
    )


def owner_authorized(authorization_header: str | None) -> bool:
    expected_user = os.getenv("OWNER_BASIC_USER", "").strip()
    expected_password = os.getenv("OWNER_BASIC_PASSWORD", "")
    if not expected_user or not expected_password:
        return False
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(
            authorization_header[6:].strip(),
            validate=True,
        ).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    if ":" not in decoded:
        return False
    user, password = decoded.split(":", 1)
    return hmac.compare_digest(user.encode(), expected_user.encode()) and hmac.compare_digest(
        password.encode(), expected_password.encode()
    )


def backend_proxy_token() -> str:
    return os.getenv("AI_BACKEND_PROXY_TOKEN", "").strip()

