"""Isolated HTTP contract and secret-leak regression tests for the backend.

All provider calls are monkeypatched. No real API key or provider request is used.
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
def backend_url(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def request(url, method="GET", body=None):
    req = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def test_http_health_without_key_is_200_and_reports_unconfigured(backend_url):
    status, body = request(backend_url + "/api/health")
    payload = json.loads(body)
    assert status == 200
    assert payload["status"] == "PASS"
    assert payload["provider_configured"] is False


def test_http_models_without_key_fails_closed(backend_url, monkeypatch):
    def must_not_call_provider():
        raise AssertionError("provider should not be called without a key")

    monkeypatch.setattr(server, "fetch_openai_model_ids", must_not_call_provider)
    status, body = request(backend_url + "/api/models")
    assert status == 503
    assert json.loads(body)["error"] == "PROVIDER_NOT_CONFIGURED"


def test_http_chat_without_key_fails_closed(backend_url, monkeypatch):
    def must_not_call_provider(*args, **kwargs):
        raise AssertionError("provider should not be called without a key")

    monkeypatch.setattr(server, "call_openai", must_not_call_provider)
    status, body = request(
        backend_url + "/api/chat",
        method="POST",
        body=b'{"message":"hello"}',
    )
    assert status == 503
    assert json.loads(body)["error"] == "PROVIDER_NOT_CONFIGURED"


def test_http_research_is_explicitly_unconfigured(backend_url):
    status, body = request(backend_url + "/api/research", method="POST", body=b"")
    payload = json.loads(body)
    assert status == 501
    assert payload["error"] == "RESEARCH_PROVIDER_UNCONFIGURED"
    assert payload["request_id"]


def test_http_invalid_json_returns_400(backend_url):
    status, body = request(
        backend_url + "/api/chat",
        method="POST",
        body=b"{invalid-json",
    )
    assert status == 400
    assert json.loads(body)["error"] == "INVALID_JSON"


def test_http_blank_message_returns_400_before_provider_call(backend_url, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "OMEGA_TEST_ONLY_NOT_A_REAL_KEY")

    def must_not_call_provider(*args, **kwargs):
        raise AssertionError("provider should not be called for an invalid message")

    monkeypatch.setattr(server, "call_openai", must_not_call_provider)
    status, body = request(
        backend_url + "/api/chat",
        method="POST",
        body=b'{"message":"   "}',
    )
    assert status == 400
    assert json.loads(body)["error"] == "MESSAGE_REQUIRED"


def test_provider_exception_cannot_leak_secret_to_response_or_logs(
    backend_url, monkeypatch, capsys
):
    secret = "OMEGA_SECRET_SENTINEL_DO_NOT_LOG"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    def simulated_provider_failure(*args, **kwargs):
        raise RuntimeError("simulated provider exception containing " + secret)

    # Test-only bypass of the unfinished owner identity boundary to exercise
    # sanitized provider-error behavior. This is NOT a real owner authorization.
    monkeypatch.setattr(server, "owner_execution_authorized", lambda: True)
    monkeypatch.setattr(server, "call_openai", simulated_provider_failure)
    status, body = request(
        backend_url + "/api/chat",
        method="POST",
        body=b'{"message":"hello"}',
    )
    captured = capsys.readouterr()
    assert status == 502
    assert secret not in body
    assert secret not in captured.out


def test_root_health_alias_is_not_defined(backend_url):
    status, body = request(backend_url + "/health")
    assert status == 404
    assert json.loads(body)["error"] == "NOT_FOUND"


def test_http_json_array_is_rejected(backend_url):
    status, body = request(
        backend_url + "/api/chat",
        method="POST",
        body=b"[]",
    )
    assert status == 400
    assert json.loads(body)["error"] == "JSON_OBJECT_REQUIRED"


def test_http_non_array_attachments_are_rejected(backend_url, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "OMEGA_TEST_ONLY_NOT_A_REAL_KEY")

    def must_not_call_provider(*args, **kwargs):
        raise AssertionError("provider should not be called for invalid attachments")

    monkeypatch.setattr(server, "call_openai", must_not_call_provider)
    status, body = request(
        backend_url + "/api/chat",
        method="POST",
        body=b'{"message":"hello","attachments":{}}',
    )
    assert status == 400
    assert json.loads(body)["error"] == "ATTACHMENTS_MUST_BE_ARRAY"
