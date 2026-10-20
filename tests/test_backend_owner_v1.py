"""Real P-256 signature/replay HTTP integration, synthetic provider; no real credentials."""
import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import owner_auth_v1 as auth
import server

server_execution_default = server.owner_execution_authorized


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


@pytest.fixture
def gate(tmp_path, monkeypatch):
    owner = ec.generate_private_key(ec.SECP256R1())
    device = ec.generate_private_key(ec.SECP256R1())
    der = lambda k: k.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setenv("OMEGA_OWNER_ID", "owner-test")
    monkeypatch.setenv("OMEGA_DEVICE_ID", "device-test")
    monkeypatch.setenv("OMEGA_OWNER_PUBLIC_DER_B64", b64(der(owner)))
    monkeypatch.setenv("OMEGA_DEVICE_PUBLIC_DER_B64", b64(der(device)))
    monkeypatch.setenv("OMEGA_NONCE_DB", str(tmp_path / "nonce.sqlite"))
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC_KEY_NEVER_TRANSMITTED")
    # Test-only escape hatch supplied by pytest, not a runtime configuration.
    monkeypatch.setattr(server, "owner_execution_authorized", lambda: True)
    def fake_call(message, attachments):
        assert message == "Merhaba"
        assert not attachments
        return "SENTETIK_YANIT", "synthetic-model"
    monkeypatch.setattr(server, "call_openai", fake_call)
    server._rate_buckets.clear()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield ("http://127.0.0.1:" + str(httpd.server_port), owner, device)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def signed_headers(owner, device, raw, *, timestamp=None, nonce=None, device_identity="device-test"):
    ts = str(int(time.time()) if timestamp is None else timestamp)
    nonce = nonce or uuid.uuid4().hex
    proof = auth.canonical("POST", auth.PATH, raw, ts, nonce, "owner-test", device_identity)
    return {
        "Content-Type": "application/json",
        "X-Omega-Owner-Id": "owner-test",
        "X-Omega-Device-Id": device_identity,
        "X-Omega-Timestamp": ts,
        "X-Omega-Nonce": nonce,
        "X-Omega-Owner-Proof": b64(owner.sign(proof, ec.ECDSA(hashes.SHA256()))),
        "X-Omega-Device-Proof": b64(device.sign(proof, ec.ECDSA(hashes.SHA256()))),
    }


def post(url, raw, headers):
    req = urllib.request.Request(url + auth.PATH, data=raw, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_unprovisioned_blocks_before_provider(gate, monkeypatch):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    monkeypatch.delenv("OMEGA_OWNER_PUBLIC_DER_B64")
    status, data = post(url, raw, signed_headers(owner, device, raw))
    assert (status, data["error"]) == (503, "OWNER_IDENTITY_NOT_PROVISIONED")


def test_verified_owner_device_to_existing_provider(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    status, data = post(url, raw, signed_headers(owner, device, raw))
    assert status == 200
    assert data["text"] == "SENTETIK_YANIT"
    assert data["contract"] == "OMEGA-OWNER-API-V1"


def test_replay_is_rejected_after_success(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    headers = signed_headers(owner, device, raw)
    assert post(url, raw, headers)[0] == 200
    status, data = post(url, raw, headers)
    assert (status, data["error"]) == (403, "OWNER_AUTH_REPLAY_OR_STORAGE_DENIED")


def test_modified_signed_body_denied(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    status, data = post(url, b'{"message":"other"}', signed_headers(owner, device, raw))
    assert status == 403 and data["error"] == "OWNER_AUTH_DENIED"


def test_stale_timestamp_denied(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    status, data = post(url, raw, signed_headers(owner, device, raw, timestamp=int(time.time()) - 120))
    assert (status, data["error"]) == (403, "OWNER_AUTH_EXPIRED")


def test_wrong_device_denied(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    status, data = post(url, raw, signed_headers(owner, device, raw, device_identity="unknown-device"))
    assert (status, data["error"]) == (403, "OWNER_IDENTITY_DENIED")


def test_missing_device_signature_denied(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    headers = signed_headers(owner, device, raw)
    del headers["X-Omega-Device-Proof"]
    status, data = post(url, raw, headers)
    assert (status, data["error"]) == (403, "OWNER_AUTH_REQUIRED")


def test_invalid_signature_denied(gate):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    other_key = ec.generate_private_key(ec.SECP256R1())
    status, data = post(url, raw, signed_headers(owner, other_key, raw))
    assert (status, data["error"]) == (403, "OWNER_AUTH_DENIED")


def test_missing_provider_key_blocks_after_auth(gate, monkeypatch):
    url, owner, device = gate
    raw = b'{"message":"Merhaba"}'
    monkeypatch.delenv("OPENAI_API_KEY")
    status, data = post(url, raw, signed_headers(owner, device, raw))
    assert (status, data["error"]) == (503, "PROVIDER_NOT_CONFIGURED")


def test_valid_signatures_never_authorize_live_execution_without_enrollment(gate, monkeypatch):
    url, owner, device = gate
    monkeypatch.setattr(server, "owner_execution_authorized", lambda: False)
    def no_provider(*args, **kwargs):
        raise AssertionError("Unenrolled Owner must not reach provider")
    monkeypatch.setattr(server, "call_openai", no_provider)
    raw = b'{"message":"Merhaba"}'
    status, body = post(url, raw, signed_headers(owner, device, raw))
    assert (status, body["error"]) == (403, "OWNER_EXECUTION_NOT_APPROVED")


def test_runtime_env_switch_cannot_enable_owner_execution(gate, monkeypatch):
    url, owner, device = gate
    monkeypatch.setattr(server, "owner_execution_authorized", server_execution_default)
    monkeypatch.setenv("OMEGA_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("OMEGA_OWNER_VERIFIED", "true")
    raw = b'{"message":"Merhaba"}'
    status, body = post(url, raw, signed_headers(owner, device, raw))
    assert status == 403
    assert body["error"] == "OWNER_EXECUTION_NOT_APPROVED"
