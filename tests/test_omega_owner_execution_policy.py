"""Fail-closed owner execution checks on all HTTP and direct provider paths.

Only synthetic secrets; actual network calls to providers are forbidden.
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import server


@pytest.fixture
def local_api(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC_CI_NOT_A_CREDENTIAL")
    monkeypatch.setenv("OMEGA_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("OMEGA_OWNER_VERIFIED", "true")
    assert server.owner_execution_authorized() is False
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    runner = threading.Thread(target=httpd.serve_forever, daemon=True)
    runner.start()
    try:
        yield "http://127.0.0.1:" + str(httpd.server_port)
    finally:
        httpd.shutdown()
        httpd.server_close()
        runner.join(timeout=3)


def call(url, *, body=None, headers=None):
    request = urllib.request.Request(
        url, method="POST" if body is not None else "GET",
        data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_plain_chat_denies_even_with_key_and_spoofed_headers(local_api, monkeypatch):
    monkeypatch.setattr(server, "call_openai",
                        lambda *a, **kw: pytest.fail("provider was invoked"))
    status, body = call(
        local_api + "/api/chat", body=b'{"message":"hello"}',
        headers={"X-Omega-Owner-Id": "owner", "X-Forwarded-For": "1.2.3.4",
                 "Authorization": "Bearer test"})
    assert (status, body["error"]) == (403, "OWNER_EXECUTION_NOT_APPROVED")


def test_models_denied_without_discovery_egress(local_api, monkeypatch):
    monkeypatch.setattr(server, "fetch_openai_model_ids",
                        lambda: pytest.fail("provider discovery was invoked"))
    status, body = call(local_api + "/api/models")
    assert (status, body["error"]) == (403, "OWNER_EXECUTION_NOT_APPROVED")


def test_direct_provider_functions_reject_unenrolled_owner(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC_CI_NOT_A_CREDENTIAL")
    monkeypatch.setattr(server.urllib.request, "urlopen",
                        lambda *a, **kw: pytest.fail("network request attempted"))
    with pytest.raises(RuntimeError, match="OWNER_EXECUTION_NOT_APPROVED"):
        server.call_openai("hello", [])
    with pytest.raises(RuntimeError, match="OWNER_EXECUTION_NOT_APPROVED"):
        server.fetch_openai_model_ids()


def test_health_and_owner_status_truthfully_report_execution_disabled(local_api):
    status, health = call(local_api + "/api/health")
    assert status == 200
    assert health["owner_identity_verified"] is False
    assert health["execution_enabled"] is False
    status, owner = call(local_api + "/api/owner/status")
    assert status == 200
    assert owner["owner_identity_verified"] is False
    assert owner["execution_enabled"] is False


def test_forwarded_header_cannot_change_rate_limit_identity():
    assert server.client_key({"X-Forwarded-For": "8.8.8.8"}, "127.0.0.1") == "127.0.0.1"


def test_untrusted_query_is_not_logged(local_api, capsys):
    marker = "QUERY_SECRET_SENTINEL_MUST_STAY_PRIVATE"
    status, _ = call(local_api + "/api/models?token=" + marker)
    assert status == 403
    printed = capsys.readouterr().out
    assert marker not in printed
