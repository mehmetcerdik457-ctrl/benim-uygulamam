"""OMEGA-027: isolated signature/issuer/audience/time/nonce/replay/PKCE tests."""

import base64
import hashlib
import json
from datetime import datetime, timezone
from secrets import token_urlsafe

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from omega_mvi.security.offline_contract import SecurityDenied, require_live_oidc
from omega_mvi.security.oidc_fixture import (
    ISSUER, AUDIENCE, SyntheticVerifier, verify_pkce_fixture,
)

NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
NONCE = "synthetic-nonce-for-one-session"
ACTION = "repository:read"


def _enc(item):
    return base64.urlsafe_b64encode(json.dumps(item, separators=(",", ":")).encode()).decode().rstrip("=")


def _signed(key, *, header=None, claims=None):
    hdr = {"typ": "JWT", "alg": "EdDSA", "kid": "synthetic-kid-1"}
    hdr.update(header or {})
    body = {"iss": ISSUER, "aud": AUDIENCE, "sub": "synthetic-user-1",
            "nonce": NONCE, "jti": "synthetic-jti-one", "scope": ACTION,
            "iat": int(NOW.timestamp()) - 10, "nbf": int(NOW.timestamp()) - 10,
            "exp": int(NOW.timestamp()) + 60}
    body.update(claims or {})
    signed = _enc(hdr) + "." + _enc(body)
    signature = key.sign(signed.encode())
    return signed + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")


@pytest.fixture
def oidc_fixture():
    # New throwaway signing key each test. Never serialized, logged or exported.
    key = Ed25519PrivateKey.generate()
    verifier = SyntheticVerifier({"synthetic-kid-1": key.public_key()})
    return key, verifier


def test_signed_fixture_binds_issuer_audience_nonce_time_and_scope(oidc_fixture):
    key, verifier = oidc_fixture
    token = _signed(key)
    assert verifier.verify(token, expected_nonce=NONCE, action=ACTION, now=NOW) == "synthetic-user-1"
    with pytest.raises(SecurityDenied, match="SYNTHETIC_IDENTITY_DENIED"):
        verifier.verify(token, expected_nonce=NONCE, action=ACTION, now=NOW)  # replay
    with pytest.raises(SecurityDenied, match="OIDC_TRUST_NOT_CONFIGURED"):
        require_live_oidc(token)  # valid fixture NEVER changes live gate


@pytest.mark.parametrize("claims", [
    {"iss": "https://untrusted.invalid"},
    {"aud": "another-app"},
    {"nonce": "synthetic-nonce-other-session"},
    {"scope": "backup:fixture"},
    {"sub": "real-user"},
    {"jti": "bad-id"},
    {"iat": int(NOW.timestamp()) + 1},
    {"nbf": int(NOW.timestamp()) + 1},
    {"exp": int(NOW.timestamp())},
    {"exp": int(NOW.timestamp()) + 3600},
    {"exp": True},
    {"iat": False},
    {"aud": [AUDIENCE, "confused-client"]},
])
def test_reject_untrusted_claims(oidc_fixture, claims):
    key, verifier = oidc_fixture
    with pytest.raises(SecurityDenied, match="SYNTHETIC_IDENTITY_DENIED"):
        verifier.verify(_signed(key, claims=claims), expected_nonce=NONCE, action=ACTION, now=NOW)


@pytest.mark.parametrize("header", [
    {"alg": "none"},
    {"alg": "HS256"},
    {"kid": "untrusted-key"},
    {"jku": "https://evil.invalid/jwks.json"},
    {"jwk": {"kty": "oct", "k": "untrusted"}},
    {"crit": ["x5u"]},
])
def test_reject_untrusted_signature_alg_and_key_provision(oidc_fixture, header):
    key, verifier = oidc_fixture
    with pytest.raises(SecurityDenied, match="SYNTHETIC_IDENTITY_DENIED"):
        verifier.verify(_signed(key, header=header), expected_nonce=NONCE, action=ACTION, now=NOW)


def test_reject_forged_signature_unknown_scope_and_malformed_claims(oidc_fixture):
    key, verifier = oidc_fixture
    other = Ed25519PrivateKey.generate()
    candidate = [_signed(other), "eyJhbGciOiJub25lIn0.e30.", "not-a-jwt", "x" * 6000]
    for token in candidate:
        with pytest.raises(SecurityDenied):
            verifier.verify(token, expected_nonce=NONCE, action=ACTION, now=NOW)
    with pytest.raises(SecurityDenied):
        verifier.verify(_signed(key), expected_nonce=NONCE, action="secrets:read", now=NOW)
    with pytest.raises(SecurityDenied):
        verifier.verify(_signed(key), expected_nonce=NONCE, action=ACTION, now=NOW.replace(tzinfo=None))


def test_pkce_s256_and_state_bound_and_never_live():
    verifier = token_urlsafe(48)
    state = "synthetic-state-for-fixture"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert verify_pkce_fixture(state=state, expected_state=state,
                               verifier=verifier, expected_challenge=challenge)
    for wrong in [
        {"state": "synthetic-state-other-fixture"},
        {"verifier": token_urlsafe(48)},
        {"expected_challenge": "A" * 43},
        {"verifier": "short"},
    ]:
        params = {"state": state, "expected_state": state,
                  "verifier": verifier, "expected_challenge": challenge}
        params.update(wrong)
        with pytest.raises(SecurityDenied, match="SYNTHETIC_PKCE_DENIED"):
            verify_pkce_fixture(**params)
