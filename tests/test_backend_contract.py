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



def test_fetch_openai_model_ids_uses_authenticated_models_endpoint(monkeypatch):
    import io

    # Unit-test only: fake upstream requests remain isolated.
    monkeypatch.setattr(server, "owner_execution_authorized", lambda: True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"data":[{"id":"gpt-5.6-luna"},{"id":"other-model"},{"id":7},{}]}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    assert server.fetch_openai_model_ids() == {"gpt-5.6-luna", "other-model"}
    assert captured["url"] == "https://api.openai.com/v1/models"
    assert captured["authorization"] == "Bearer test-only-not-a-real-key"
    assert captured["timeout"] <= 10


def test_fetch_openai_model_ids_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        server.fetch_openai_model_ids()
    except RuntimeError as exc:
        assert str(exc) == "PROVIDER_NOT_CONFIGURED"
    else:
        raise AssertionError("Expected missing-key failure")


def test_fetch_openai_model_ids_rejects_invalid_shape(monkeypatch):
    import io

    # Unit-test only: fake upstream requests remain isolated.
    monkeypatch.setattr(server, "owner_execution_authorized", lambda: True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"models":[]}'

    monkeypatch.setattr(server.urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())
    try:
        server.fetch_openai_model_ids()
    except ValueError as exc:
        assert str(exc) == "INVALID_MODEL_LIST_RESPONSE"
    else:
        raise AssertionError("Expected invalid-response failure")
