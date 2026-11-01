"""Fail-closed P-256 owner signature verifier for the private P1 backend.

Signs exact HTTP body bytes. The OWNER_P256_PUBLIC_KEY_PEM must be enrolled
out of band after owner/device verification; never trust a supplied public key.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import threading
import time
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

SKEW_SECONDS = 120
NONCE_LIMIT = 4096
_LOCK = threading.Lock()
_SEEN: dict[str, float] = {}


def configured() -> bool:
    return bool(os.getenv("OWNER_P256_PUBLIC_KEY_PEM", "").strip())


def signed_payload(timestamp: str, nonce: str, body: bytes) -> bytes:
    return (
        b"MEHMET_OWNER_CHAT_V1\n"
        + timestamp.encode("ascii")
        + b"\n"
        + nonce.encode("ascii")
        + b"\n"
        + hashlib.sha256(body).hexdigest().encode("ascii")
    )


def verify(headers: Mapping[str, str], body: bytes, *, now: float | None = None) -> bool:
    """Verify ECDSA-SHA256 and consume the one-use nonce atomically."""
    pem = os.getenv("OWNER_P256_PUBLIC_KEY_PEM", "").strip()
    if not pem:
        return False
    timestamp = (headers.get("X-MEH-Owner-Timestamp") or "").strip()
    nonce = (headers.get("X-MEH-Owner-Nonce") or "").strip()
    sig_encoded = (headers.get("X-MEH-Owner-Signature") or "").strip()
    if not re.fullmatch(r"[0-9]{10,13}", timestamp):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}={0,2}", sig_encoded):
        return False
    current = time.time() if now is None else now
    try:
        sent_at = int(timestamp)
        if abs(current - sent_at) > SKEW_SECONDS:
            return False
        key = serialization.load_pem_public_key(pem.encode("ascii"))
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            return False
        signature = base64.urlsafe_b64decode(sig_encoded + "=" * (-len(sig_encoded) % 4))
        key.verify(signature, signed_payload(timestamp, nonce, body), ec.ECDSA(hashes.SHA256()))
    except (ValueError, TypeError, UnicodeError, InvalidSignature):
        return False
    with _LOCK:
        expired = [n for n, t in _SEEN.items() if t <= current]
        for n in expired:
            del _SEEN[n]
        if nonce in _SEEN or len(_SEEN) >= NONCE_LIMIT:
            return False
        _SEEN[nonce] = current + SKEW_SECONDS * 2
    return True
