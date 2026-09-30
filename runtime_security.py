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



def sites_bff_configured() -> bool:
    """Return True only when a production-strength Sites BFF token exists."""
    return len(os.getenv("SITES_BFF_TOKEN", "").strip()) >= 32


def sites_bff_authorized(supplied: str | None, path: str, method: str) -> bool:
    """Authorize the dedicated Sites server credential for chat only."""
    expected = os.getenv("SITES_BFF_TOKEN", "").strip()
    candidate = (supplied or "").strip()
    if len(expected) < 32 or not candidate or len(candidate) > 256:
        return False
    if path != "/api/chat" or (method or "").upper() != "POST":
        return False
    return hmac.compare_digest(candidate.encode(), expected.encode())
