"""Offline *test-only* signed identity and PKCE contract for OMEGA-027.

NOT an OIDC provider, production JWT verifier, authentication middleware or
credential issuer. No endpoint or task authorizer imports this module.
The caller controls trusted keys ONLY in isolated synthetic tests. A real IdP,
JWKS lifecycle, token exchange, secure browser session and durable replay
ledger must be implemented/reviewed separately before authorization.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .offline_contract import SecurityDenied

ISSUER = "https://idp.synthetic.invalid"
AUDIENCE = "omega-synthetic-fixture-client"
MAX_TOKEN_LIFETIME_SECONDS = 300
ALLOWED_FIXTURE_SCOPES = frozenset({"repository:read", "inventory:read", "rag:read", "pr:read"})
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_PKCE_VERIFIER = re.compile(r"^[A-Za-z0-9._~\\-]{43,128}$")
_MAX_JWT_BYTES = 4096


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _decode_part(encoded):
    if not encoded or not _B64URL.fullmatch(encoded) or len(encoded) > _MAX_JWT_BYTES:
        raise ValueError("invalid base64url")
    data = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    # Canonical encoding only, to avoid multiple spellings of same signed input.
    if base64.urlsafe_b64encode(data).decode("ascii").rstrip("=") != encoded:
        raise ValueError("non-canonical base64url")
    return data


def _parse_json(encoded):
    item = json.loads(_decode_part(encoded).decode("utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(item, dict):
        raise ValueError("not JSON object")
    return item


def _int_claim(claims, name):
    value = claims.get(name)
    if type(value) is not int or value < 0:
        raise ValueError("invalid time claim")
    return value


@dataclass
class SyntheticVerifier:
    """In-memory verification and one-process replay rejection; fixture only."""

    trusted_public_keys: dict[str, Ed25519PublicKey]
    seen_ids: set[str] = field(default_factory=set)

    def __post_init__(self):
        if (not isinstance(self.trusted_public_keys, dict)
                or not self.trusted_public_keys
                or any(not isinstance(key, str) or not key.startswith("synthetic-kid-")
                           or not isinstance(value, Ed25519PublicKey)
                           for key, value in self.trusted_public_keys.items())):
            raise SecurityDenied("TRUSTED_FIXTURE_KEY_REQUIRED")
        self.trusted_public_keys = dict(self.trusted_public_keys)

    def verify(self, token: str, *, expected_nonce: str, action: str,
               now: datetime) -> str:
        # No decoded, signature-derived or caller-provided details ever leave errors.
        try:
            if (not isinstance(token, str) or len(token) > _MAX_JWT_BYTES
                    or token.count(".") != 2):
                raise ValueError("JWT envelope")
            if (not isinstance(now, datetime) or now.tzinfo is None
                    or now.utcoffset() != timedelta(0)):
                raise ValueError("UTC clock required")
            if not isinstance(expected_nonce, str) or not expected_nonce.startswith("synthetic-nonce-"):
                raise ValueError("nonce from trusted fixture required")
            if action not in ALLOWED_FIXTURE_SCOPES:
                raise ValueError("untrusted requested scope")
            header_enc, payload_enc, sig_enc = token.split(".")
            header = _parse_json(header_enc)
            # No token-controlled URL, alg negotiation, embedded public key or crit header.
            if (set(header) != {"typ", "alg", "kid"}
                    or header.get("typ") != "JWT" or header.get("alg") != "EdDSA"):
                raise ValueError("untrusted header")
            key = self.trusted_public_keys.get(header.get("kid"))
            if key is None:
                raise ValueError("unknown trusted key")
            sig = _decode_part(sig_enc)
            key.verify(sig, (header_enc + "." + payload_enc).encode("ascii"))
            claims = _parse_json(payload_enc)
            if claims.get("iss") != ISSUER or claims.get("aud") != AUDIENCE:
                raise ValueError("issuer or audience mismatch")
            subject, nonce, jti, scope = (claims.get("sub"), claims.get("nonce"),
                                          claims.get("jti"), claims.get("scope"))
            if (not isinstance(subject, str) or not subject.startswith("synthetic-user-")
                    or not isinstance(nonce, str)
                    or not compare_digest(nonce, expected_nonce)
                    or not isinstance(jti, str) or not jti.startswith("synthetic-jti-")
                    or not isinstance(scope, str) or scope not in ALLOWED_FIXTURE_SCOPES
                    or scope != action):
                raise ValueError("identity, nonce or scope mismatch")
            iat, nbf, exp = (_int_claim(claims, name) for name in ("iat", "nbf", "exp"))
            now_seconds = int(now.timestamp())
            if not (iat <= now_seconds and nbf <= now_seconds < exp
                    and nbf >= iat and 0 < exp - iat <= MAX_TOKEN_LIFETIME_SECONDS):
                raise ValueError("token outside trusted time window")
            if jti in self.seen_ids:
                raise ValueError("token replay")
            self.seen_ids.add(jti)
            return subject  # synthetic subject only: NEVER authorize a live request
        except (ValueError, TypeError, AttributeError, KeyError, UnicodeError,
                InvalidSignature, OverflowError, MemoryError) as exc:
            raise SecurityDenied("SYNTHETIC_IDENTITY_DENIED") from None


def verify_pkce_fixture(*, state: str, expected_state: str,
                        verifier: str, expected_challenge: str) -> bool:
    """Fixture state/PKCE S256 binding, NOT an OAuth authorization-code exchange."""
    if (not isinstance(state, str) or not isinstance(expected_state, str)
            or not state.startswith("synthetic-state-")
            or not expected_state.startswith("synthetic-state-")
            or not isinstance(verifier, str) or not _PKCE_VERIFIER.fullmatch(verifier)
            or not isinstance(expected_challenge, str)
            or len(expected_challenge) != 43
            or not _B64URL.fullmatch(expected_challenge)):
        raise SecurityDenied("SYNTHETIC_PKCE_DENIED")
    actual = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    if not compare_digest(state, expected_state) or not compare_digest(actual, expected_challenge):
        raise SecurityDenied("SYNTHETIC_PKCE_DENIED")
    return True
