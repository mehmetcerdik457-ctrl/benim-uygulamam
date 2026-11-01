"""Guide adapter contract tests; provider transport is mocked, never live."""
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import server

GUIDE_PROMPT = (
    "You are the OpenAI task engine for this app. Follow existing app policy, "
    "avoid side effects unless approved, and return concise results."
)


def fake_provider(monkeypatch, response):
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(response).encode()

    def send(request, **_):
        assert request.full_url == "https://api.openai.com/v1/responses"
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "fake-unit-test-key")
    monkeypatch.setattr(server, "DEFAULT_MODEL", "gpt-4.1")
    monkeypatch.setattr(urllib.request, "urlopen", send)
    return captured


def test_exact_guide_prompt_request_metadata_and_actual_response_id(monkeypatch):
    calls = fake_provider(monkeypatch, {"id": "resp_provider_fixture", "output_text": "MOCK_ONLY"})
    result = server.runKralAiTask({"userMessage": "KRAL task", "requestId": "request-fixture"})
    assert result == {"text": "MOCK_ONLY", "model": "gpt-4.1", "responseId": "resp_provider_fixture"}
    assert len(calls) == 1
    payload = calls[0]
    assert payload["model"] == "gpt-4.1"
    assert payload["input"][0] == {"role": "system", "content": GUIDE_PROMPT}
    assert payload["input"][1]["content"][0]["text"] == "KRAL task"
    assert payload["metadata"] == {"request_id": "request-fixture"}
    assert payload["store"] is False


def test_client_tools_prompt_and_approval_are_not_provider_configuration(monkeypatch):
    calls = fake_provider(monkeypatch, {"id": "resp_tools_fixture", "output_text": "MOCK_ONLY"})
    task = {
        "userMessage": "Do not execute tools", "requestId": "request-tools-fixture",
        "system_prompt": "UNTRUSTED_POLICY",
        "tools": [{"type": "function", "name": "delete_everything"}],
        "approval_token": "UNTRUSTED_APPROVAL",
    }
    server.runKralAiTask(task)
    payload = calls[0]
    assert payload["input"][0]["content"] == GUIDE_PROMPT
    assert "tools" not in payload and "approval_token" not in payload
    assert "UNTRUSTED_POLICY" not in json.dumps(payload)
    assert "delete_everything" not in json.dumps(payload)


def test_missing_key_fails_before_transport(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def no_network(*_, **__):
        pytest.fail("Unconfigured adapter must not call the provider")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    with pytest.raises(RuntimeError, match="^OPENAI_NOT_CONFIGURED$"):
        server.runKralAiTask({"userMessage": "hello", "requestId": "request-no-key"})


@pytest.mark.parametrize("status,expected", [
    (401, "OPENAI_ACCESS_DENIED"),
    (403, "OPENAI_MODEL_NOT_AVAILABLE"),
    (404, "OPENAI_MODEL_NOT_AVAILABLE"),
])
def test_typed_access_and_model_failure_without_retry_or_raw_error(monkeypatch, status, expected):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-unit-test-key")
    attempts = []

    def denied(*_, **__):
        attempts.append(status)
        raise urllib.error.HTTPError(
            server.OPENAI_URL, status, "PRIVATE_UPSTREAM_BODY", {},
            io.BytesIO(b'{"error":{"message":"PRIVATE_UPSTREAM_BODY"}}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", denied)
    with pytest.raises(server.KralOpenAIError) as raised:
        server.runKralAiTask({"userMessage": "hello", "requestId": "request-denied"})
    assert str(raised.value) == expected
    assert raised.value.upstream_status == status
    assert "PRIVATE_UPSTREAM_BODY" not in str(raised.value)
    assert attempts == [status]


def test_missing_provider_id_never_fabricates_a_success_receipt(monkeypatch):
    fake_provider(monkeypatch, {"output_text": "MOCK_ONLY"})
    with pytest.raises(RuntimeError, match="^PROVIDER_RESPONSE_ID_MISSING$"):
        server.runKralAiTask({"userMessage": "hello", "requestId": "request-id-missing"})

