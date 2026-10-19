"""Fail-closed owner authentication tests against a local HTTP backend.

No real owner identity, provider request, or credential is used.
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import server


@pytest.fixture
def local_backend(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC_NOT_REAL")
    server._rate_buckets.clear()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join(timeout=2)
        server._rate_buckets.clear()


def local_request(base, path, method, headers=None):
    body = b'{"message":"synthetic"}' if method == "POST" else None
    req = urllib.request.Request(
        base + path, data=body, method=method, headers=headers or {}
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer SYNTHETIC_CLAIM"},
        {"X-Owner-ID": "OWNER"},
        {"X-Auth-Level": "admin"},
        {"X-Forwarded-User": "owner"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Authenticated-User": "owner"},
    ],
)
def test_unverified_headers_never_authorize_provider(
    local_backend, monkeypatch, headers
):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("provider")
        raise AssertionError("Provider must never be called")

    monkeypatch.setattr(server, "call_openai", forbidden)
    monkeypatch.setattr(server, "fetch_openai_model_ids", forbidden)

    chat_status, chat = local_request(
        local_backend, "/api/chat", "POST", headers
    )
    model_status, models = local_request(
        local_backend, "/api/models", "GET", headers
    )
    assert chat_status == 403
    assert chat["error"] == "OWNER_AUTH_REQUIRED"
    assert chat["request_id"]
    assert model_status == 403
    assert models["error"] == "OWNER_AUTH_REQUIRED"
    assert calls == []


def test_no_environment_toggle_can_claim_owner_auth(local_backend, monkeypatch):
    for name in (
        "OMEGA_OWNER_AUTHENTICATED",
        "OWNER_AUTH_VERIFIED",
        "OMEGA_AUTH_BYPASS",
        "OWNER_ID",
    ):
        monkeypatch.setenv(name, "true")
    assert server.owner_execution_authorized() is False
    status, response = local_request(local_backend, "/api/chat", "POST")
    assert status == 403
    assert response["error"] == "OWNER_AUTH_REQUIRED"


def test_unprovisioned_owner_is_reported_as_unprovisioned(local_backend):
    status, payload = local_request(local_backend, "/api/owner/status", "GET")
    assert status == 200
    assert payload["owner"]["AUTH_LEVEL"] == "UNPROVISIONED"
    assert payload["owner"]["AUTH_METHOD"] == "UNPROVISIONED"


def test_health_does_not_establish_owner_authorization(local_backend):
    status, payload = local_request(local_backend, "/api/health", "GET")
    assert status == 200
    assert payload["status"] == "PASS"
    assert server.owner_execution_authorized() is False
