"""OMEGA provider error handling contracts: no real provider, no real secrets."""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from backend import server


@pytest.fixture
def incoming(monkeypatch):
    monkeypatch.setenv("AI_BACKEND_PROXY_TOKEN", "synthetic-proxy-only")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-provider-not-a-key")
    monkeypatch.setattr(server, "rate_allowed", lambda *args, **kwargs: True)
    responses = []
    calls = []

    def issue(exc):
        calls.append(True)
        def fail(_message, _attachments):
            raise exc
        monkeypatch.setattr(server, "call_openai", fail)
        h = object.__new__(server.Handler)
        h.path = "/api/chat"
        h.headers = {"X-MEH-Proxy-Token": "synthetic-proxy-only"}
        h.client_address = ("127.0.0.1", 49152)
        body = json.dumps({"message": "synthetic test"}).encode()
        h.headers["Content-Length"] = str(len(body))
        h.rfile = io.BytesIO(body)

        def capture(status, payload, request_id=None):
            responses.append((status, payload))
        h._send = capture
        h.do_POST()
        return responses[-1]
    return issue, calls


def test_unexpected_provider_exception_never_reflects_sensitive_message(incoming, capsys):
    issue, calls = incoming
    bad = "sk-synthetic-private-string-do-not-log"
    status, reply = issue(RuntimeError("provider failure " + bad))
    log = capsys.readouterr().out
    assert calls == [True]
    assert status == 502
    assert reply["error"] == "INTERNAL_PROVIDER_ERROR"
    assert bad not in json.dumps(reply) and bad not in log
    assert "provider failure" not in json.dumps(reply)


def test_nonexception_runtime_error_code_is_generic(incoming, capsys):
    issue, _ = incoming
    status, reply = issue(ValueError("password=synthetic-please-redact"))
    assert status == 502
    assert reply["error"] == "INTERNAL_PROVIDER_ERROR"
    assert "password=" not in json.dumps(reply) + capsys.readouterr().out


@pytest.mark.parametrize("allowed", (
    "PROVIDER_NOT_CONFIGURED",
    "PROVIDER_MODEL_NOT_ALLOWED",
    "INVALID_OUTPUT_TOKEN_LIMIT",
    "EMPTY_PROVIDER_RESPONSE",
))
def test_known_safe_runtime_codes_only(incoming, allowed):
    issue, _ = incoming
    status, reply = issue(RuntimeError(allowed))
    assert status == 502
    assert reply["error"] == allowed


@pytest.mark.parametrize("candidate", (
    [], {}, ["invalid_api_key"], {"x":"invalid_api_key"}, 0, None,
))
def test_untrusted_provider_error_code_types_cannot_break_error_handler(
    incoming, capsys, candidate
):
    issue, _ = incoming
    body = json.dumps({"error":{"code":candidate,"type":"invalid_api_key"}}).encode()
    exc = urllib.error.HTTPError(
        "https://api.openai.com/v1/responses", 401, "Unauthorized", None,
        io.BytesIO(body)
    )
    status, reply = issue(exc)
    out = capsys.readouterr().out
    assert status == 502
    assert reply["error"] == "UPSTREAM_PROVIDER_ERROR"
    assert reply["upstream_code"] == "invalid_api_key"
    assert "Traceback" not in out


def test_allowlisted_provider_code_returns_only_safe_code(incoming):
    issue, _ = incoming
    body = json.dumps({"error":{"code":"model_not_found","message":"sk-sensitive-not-shared"}}).encode()
    exc = urllib.error.HTTPError(
        "https://api.openai.com/v1/responses", 404, "Not found", None,
        io.BytesIO(body)
    )
    status, reply = issue(exc)
    assert status == 502
    assert reply["upstream_status"] == 404
    assert reply["upstream_code"] == "model_not_found"
    assert "sk-sensitive" not in json.dumps(reply)
