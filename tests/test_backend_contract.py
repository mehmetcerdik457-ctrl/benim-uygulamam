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


def test_extract_response_text_openai_compatible_chat():
    payload = {"choices": [{"message": {"content": "açık kaynak cevap"}}]}
    assert server.extract_response_text(payload) == "açık kaynak cevap"


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


def test_openai_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert server.openai_configured() is False
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    assert server.openai_configured() is True


def test_huggingface_configured(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert server.huggingface_configured() is False
    monkeypatch.setenv("HF_TOKEN", "test-only-not-a-real-token")
    assert server.huggingface_configured() is True


def test_provider_normalization_and_profiles():
    assert server.normalize_provider("hf") == "huggingface"
    assert server.normalize_provider("openai") == "openai"
    assert server.normalize_profile("max") == "max"
    assert server.select_model("openai", profile="max") == "gpt-6-astra"
    assert server.select_model("openai", profile="balanced") == "gpt-6-sol"
    assert server.select_model("openai", profile="fast") == "gpt-6-luna"
    assert server.select_model("huggingface", profile="balanced") == "openai/gpt-oss-20b:preferred"


def test_provider_and_model_fail_closed():
    for bad in ("other", "local"):
        try:
            server.normalize_provider(bad)
        except ValueError as exc:
            assert str(exc) == "PROVIDER_NOT_ALLOWED"
        else:
            raise AssertionError("unexpected provider accepted")

    try:
        server.select_model("openai", requested_model="not-allowed")
    except ValueError as exc:
        assert str(exc) == "MODEL_NOT_ALLOWED"
    else:
        raise AssertionError("unexpected model accepted")


def test_proxy_configured_false_without_token(monkeypatch):
    monkeypatch.delenv("AI_BACKEND_PROXY_TOKEN", raising=False)
    assert server.proxy_configured() is False
    assert server.proxy_authorized({}) is False


def test_proxy_configured_and_authorized(monkeypatch):
    monkeypatch.setenv("AI_BACKEND_PROXY_TOKEN", "test-proxy-token")
    assert server.proxy_configured() is True
    assert server.proxy_authorized({"X-MEH-Proxy-Token": "test-proxy-token"}) is True
    assert server.proxy_authorized({"X-MEH-Proxy-Token": "wrong"}) is False
