"""Additional attachment-shape matrix for PROJECT OMEGA audit 004.

Uses only a sentinel key and a monkeypatched provider; no real network/provider calls.
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
    monkeypatch.setenv("OPENAI_API_KEY", "OMEGA_TEST_ONLY_NOT_A_REAL_KEY")
    monkeypatch.setattr(server, "owner_execution_authorized", lambda: True)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def post_chat(url, attachments_json):
    body = (
        '{"message":"hello","attachments":'
        + attachments_json
        + "}"
    ).encode("utf-8")
    req = urllib.request.Request(
        url + "/api/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


@pytest.mark.parametrize(
    ("value", "expected_status", "expected_error"),
    [
        ("null", 200, None),
        ("{}", 400, "ATTACHMENTS_MUST_BE_ARRAY"),
        ("false", 400, "ATTACHMENTS_MUST_BE_ARRAY"),
        ("0", 400, "ATTACHMENTS_MUST_BE_ARRAY"),
        ('""', 400, "ATTACHMENTS_MUST_BE_ARRAY"),
        ("[]", 200, None),
        ('[{"name":"note.txt","type":"text/plain"}]', 200, None),
    ],
)
def test_attachments_json_shape_matrix(
    backend_url, monkeypatch, value, expected_status, expected_error
):
    calls = []

    def fake_provider(message, attachments):
        calls.append((message, attachments))
        return "mocked response", "mock-model"

    monkeypatch.setattr(server, "call_openai", fake_provider)
    status, body = post_chat(backend_url, value)
    payload = json.loads(body)

    assert status == expected_status
    if expected_error:
        assert payload["error"] == expected_error
        assert calls == []
    else:
        assert payload["text"] == "mocked response"
        assert len(calls) == 1
        if value == "null" or value == "[]":
            assert calls[0][1] == []
        else:
            assert isinstance(calls[0][1], list)
