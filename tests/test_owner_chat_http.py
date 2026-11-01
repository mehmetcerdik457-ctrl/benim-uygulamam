"""HTTP-level owner gateway tests; provider calls are mocked, never live."""
import base64
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import owner_p256
import server
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


@contextmanager
def running_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(httpd.server_address[1])
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def call(base, path, body, headers):
    req = urllib.request.Request(base + path, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def headers_for(key, body, nonce):
    timestamp = str(int(time.time()))
    sig = key.sign(owner_p256.signed_payload(timestamp, nonce, body), ec.ECDSA(hashes.SHA256()))
    return {
        "X-MEH-Proxy-Token": "proxy-test-secret",
        "X-MEH-Owner-Timestamp": timestamp,
        "X-MEH-Owner-Nonce": nonce,
        "X-MEH-Owner-Signature": base64.urlsafe_b64encode(sig).decode().rstrip("="),
        "Content-Type": "application/json",
    }


def test_signed_owner_chat_real_http_mock_provider(monkeypatch):
    owner_p256._SEEN.clear()
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", pub)
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-fake-provider-token")
    monkeypatch.setenv("AI_BACKEND_PROXY_TOKEN", "proxy-test-secret")
    monkeypatch.setattr(server, "call_openai", lambda *_: ("MOCK_ONLY", "test-model"))
    body = b'{"message":"hello","provider":"openai"}'
    headers = headers_for(key, body, "owner-http-nonce-001")
    with running_server() as base:
        status, data = call(base, "/api/v1/owner/chat", body, headers)
        assert status == 200 and data["text"] == "MOCK_ONLY"
        assert data["model"] == "test-model"
        replay_status, data = call(base, "/api/v1/owner/chat", body, headers)
        assert replay_status == 401 and data["error"] == "OWNER_SIGNATURE_INVALID"
        bad_status, _ = call(base, "/api/v1/owner/chat", b'{"message":"changed"}', headers)
        assert bad_status == 401


def test_owner_endpoint_fail_closed_and_legacy_proxy(monkeypatch):
    owner_p256._SEEN.clear()
    key = ec.generate_private_key(ec.SECP256R1())
    body = b'{"message":"hello"}'
    headers = headers_for(key, body, "owner-http-nonce-002")
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-fake-provider-token")
    monkeypatch.setenv("AI_BACKEND_PROXY_TOKEN", "proxy-test-secret")
    monkeypatch.delenv("OWNER_P256_PUBLIC_KEY_PEM", raising=False)
    monkeypatch.setattr(server, "call_openai", lambda *_: ("LEGACY_MOCK", "test-model"))
    with running_server() as base:
        status, data = call(base, "/api/v1/owner/chat", body, headers)
        assert status == 503 and data["error"] == "OWNER_P256_NOT_CONFIGURED"
        status, data = call(base, "/api/chat", body, {"X-MEH-Proxy-Token": "proxy-test-secret"})
        assert status == 200 and data["text"] == "LEGACY_MOCK"
        status, data = call(base, "/api/chat", body, {})
        assert status == 401 and data["error"] == "UNAUTHORIZED_PROXY"
