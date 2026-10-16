"""OMEGA per-request Responses token ceiling; no live API or real credentials."""
from __future__ import annotations

import json

import pytest

from backend import server


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.body if size is None or size < 0 else self.body[:size]


@pytest.fixture
def fake_provider(monkeypatch):
    captured = []

    def urlopen(req, timeout=None):
        captured.append({
            "payload": json.loads(req.data.decode("utf-8")),
            "timeout": timeout,
            "authorization": req.get_header("Authorization"),
            "url": req.full_url,
        })
        return FakeResponse(json.dumps({"output_text": "synthetic reply"}).encode())

    monkeypatch.setattr(server.urllib.request, "urlopen", urlopen)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key-not-valid")
    monkeypatch.setattr(server, "MAX_OUTPUT_TOKENS", 128)
    monkeypatch.setattr(server, "DEFAULT_MODEL", "mock-model")
    monkeypatch.setattr(server, "ALLOWED_MODELS", ("mock-model",))
    return captured


def test_default_request_keeps_original_ceiling(fake_provider):
    text, model = server.call_openai("hello", [])
    assert text == "synthetic reply" and model == "mock-model"
    assert fake_provider[0]["payload"]["max_output_tokens"] == 128
    assert fake_provider[0]["payload"]["store"] is False
    assert fake_provider[0]["url"] == server.OPENAI_URL


def test_local_limit_applies_without_mutating_global(fake_provider):
    server.call_openai("first", [], max_output_tokens=16)
    server.call_openai("second", [], max_output_tokens=32)
    server.call_openai("default", [])
    assert [x["payload"]["max_output_tokens"] for x in fake_provider] == [16, 32, 128]
    assert server.MAX_OUTPUT_TOKENS == 128


@pytest.mark.parametrize("bad", [0, -1, True, False, 129, 999, 16.0, "16", [], {}])
def test_invalid_limit_rejected_before_network(fake_provider, bad):
    with pytest.raises(RuntimeError, match="INVALID_OUTPUT_TOKEN_LIMIT"):
        server.call_openai("hello", [], max_output_tokens=bad)
    assert fake_provider == []


def test_boundary_limits_are_allowed(fake_provider):
    server.call_openai("small", [], max_output_tokens=1)
    server.call_openai("large", [], max_output_tokens=128)
    assert [r["payload"]["max_output_tokens"] for r in fake_provider] == [1, 128]


def test_invalid_global_limit_fails_before_network(fake_provider, monkeypatch):
    monkeypatch.setattr(server, "MAX_OUTPUT_TOKENS", 0)
    with pytest.raises(RuntimeError, match="INVALID_OUTPUT_TOKEN_LIMIT"):
        server.call_openai("hello", [], max_output_tokens=16)
    assert fake_provider == []


def test_absent_key_fails_without_network(fake_provider, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(RuntimeError, match="PROVIDER_NOT_CONFIGURED"):
        server.call_openai("hello", [], max_output_tokens=16)
    assert fake_provider == []


def test_empty_model_allowlist_fails_without_network(fake_provider, monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_MODELS", ())
    with pytest.raises(RuntimeError, match="PROVIDER_MODEL_NOT_ALLOWED"):
        server.call_openai("hello", [], max_output_tokens=16)
    assert fake_provider == []


def test_model_input_and_auth_are_synthetic(fake_provider):
    server.call_openai("hi", [], max_output_tokens=16)
    assert fake_provider[0]["payload"]["model"] == "mock-model"
    assert fake_provider[0]["authorization"] == "Bearer synthetic-key-not-valid"
    assert fake_provider[0]["payload"]["input"][0]["content"][0]["text"] == "hi"


def test_unexpected_empty_response_is_denied(fake_provider, monkeypatch):
    def empty_response(req, timeout=None):
        return FakeResponse(b'{"output_text":""}')
    monkeypatch.setattr(server.urllib.request, "urlopen", empty_response)
    with pytest.raises(RuntimeError, match="EMPTY_PROVIDER_RESPONSE"):
        server.call_openai("hello", [], max_output_tokens=16)


def test_simultaneous_requests_keep_independent_caps(fake_provider, monkeypatch):
    """Both requests enter the fake upstream together; neither touches global state."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    rendezvous = Barrier(2, timeout=5)
    payloads = []

    def concurrent_urlopen(req, timeout=None):
        payloads.append(json.loads(req.data.decode("utf-8"))["max_output_tokens"])
        rendezvous.wait()
        return FakeResponse(b'{"output_text":"synthetic reply"}')

    monkeypatch.setattr(server.urllib.request, "urlopen", concurrent_urlopen)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(server.call_openai, "first", [], max_output_tokens=16),
            pool.submit(server.call_openai, "second", [], max_output_tokens=32),
        ]
        assert [job.result(timeout=8)[0] for job in futures] == [
            "synthetic reply", "synthetic reply",
        ]
    assert sorted(payloads) == [16, 32]
    assert server.MAX_OUTPUT_TOKENS == 128


def test_configured_model_not_in_allowlist_is_denied_before_network(fake_provider, monkeypatch):
    monkeypatch.setattr(server, "DEFAULT_MODEL", "unexpected-model")
    with pytest.raises(RuntimeError, match="PROVIDER_MODEL_NOT_ALLOWED"):
        server.call_openai("hello", [], max_output_tokens=16)
    assert fake_provider == []


def test_configured_model_mismatch_never_falls_back_to_first_model(fake_provider, monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_MODELS", ("other-model", "another-model"))
    with pytest.raises(RuntimeError, match="PROVIDER_MODEL_NOT_ALLOWED"):
        server.call_openai("hello", [])
    assert fake_provider == []


def test_provider_response_is_read_with_hard_ceiling(fake_provider, monkeypatch):
    """Upstream read must be bounded, not a bare response.read()."""
    read_sizes = []
    class RecordingResponse(FakeResponse):
        def read(self, size=-1):
            read_sizes.append(size)
            return super().read(size)
    monkeypatch.setattr(
        server.urllib.request, "urlopen",
        lambda req, timeout=None: RecordingResponse(b'{"output_text":"safe"}')
    )
    assert server.call_openai("hello", [], max_output_tokens=16)[0] == "safe"
    assert read_sizes == [server.MAX_PROVIDER_RESPONSE_BYTES + 1]


def test_provider_large_payload_is_rejected_not_logged(fake_provider, monkeypatch):
    """A provider ignoring output-token limits must not exhaust memory."""
    big = b'{"output_text":"' + b'X' * (server.MAX_PROVIDER_RESPONSE_BYTES + 1) + b'"}'
    monkeypatch.setattr(
        server.urllib.request, "urlopen",
        lambda req, timeout=None: FakeResponse(big)
    )
    with pytest.raises(RuntimeError, match="UPSTREAM_RESPONSE_TOO_LARGE"):
        server.call_openai("hello", [], max_output_tokens=16)


@pytest.mark.parametrize("body", [b"[]", b'"wrong shape"', b"42", b"null"])
def test_non_object_provider_response_fails_closed(fake_provider, monkeypatch, body):
    monkeypatch.setattr(
        server.urllib.request, "urlopen",
        lambda req, timeout=None: FakeResponse(body)
    )
    with pytest.raises(RuntimeError, match="INVALID_PROVIDER_RESPONSE"):
        server.call_openai("hello", [], max_output_tokens=16)


def test_bounded_json_accepted_at_one_megabyte(fake_provider, monkeypatch):
    # Max-size check is byte-exact and does not wrongly reject valid JSON.
    suffix = b'{"output_text":"'
    trailer = b'"}'
    body = suffix + b'a' * (server.MAX_PROVIDER_RESPONSE_BYTES-len(suffix)-len(trailer)) + trailer
    assert len(body) == server.MAX_PROVIDER_RESPONSE_BYTES
    monkeypatch.setattr(
        server.urllib.request, "urlopen",
        lambda req, timeout=None: FakeResponse(body)
    )
    reply, _ = server.call_openai("hello", [], max_output_tokens=16)
    assert len(reply) == server.MAX_PROVIDER_RESPONSE_BYTES-len(suffix)-len(trailer)
