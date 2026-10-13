import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server


def test_extract_response_text_nested():
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Merhaba Mehmet"}
                ],
            }
        ]
    }
    assert server.extract_response_text(payload) == "Merhaba Mehmet"


def test_extract_response_text_direct():
    assert server.extract_response_text({"output_text": "ok"}) == "ok"


def test_build_input_keeps_attachment_metadata_only():
    text = server.build_input(
        "incele",
        [
            {
                "name": "a.txt",
                "type": "text/plain",
                "size": 12,
                "sha256": "abc",
                "source": "file",
                "raw": "SECRET_FILE_CONTENT",
            }
        ],
    )
    assert "a.txt" in text
    assert "abc" in text
    assert "SECRET_FILE_CONTENT" not in text


def test_rate_limit_window(monkeypatch):
    monkeypatch.setattr(server, "RATE_LIMIT_PER_MINUTE", 2)
    server._rate_buckets.clear()
    assert server.rate_allowed("x", 100.0)
    assert server.rate_allowed("x", 101.0)
    assert not server.rate_allowed("x", 102.0)
    assert server.rate_allowed("x", 161.1)


def test_configured_false_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert server.configured() is False


def test_configured_true_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    assert server.configured() is True


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_call_openai_sends_bearer_header_offline(monkeypatch):
    import json as _json

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["timeout"] = timeout
        return _FakeResponse(_json.dumps({"output_text": "tamam"}).encode())

    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    text, model = server.call_openai("selam", [])
    assert text == "tamam"
    assert model in server.ALLOWED_MODELS
    assert captured["headers"]["authorization"] == "Bearer " + "test-only-not-a-real-key"
    assert captured["timeout"] == server.UPSTREAM_TIMEOUT_SECONDS


def test_call_openai_fails_closed_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        server.call_openai("selam", [])
    except RuntimeError as exc:
        assert str(exc) == "PROVIDER_NOT_CONFIGURED"
    else:
        raise AssertionError("expected fail-closed")
