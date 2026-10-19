"""Model-routing fail-closed contract: no provider calls for unapproved models.

Only synthetic keys and stub network functions are used by this suite.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import server


def test_explicit_default_is_selected(monkeypatch):
    monkeypatch.setattr(server, "DEFAULT_MODEL", "omega-approved")
    monkeypatch.setattr(server, "ALLOWED_MODELS", ("omega-approved", "omega-second"))
    assert server.select_model() == "omega-approved"


@pytest.mark.parametrize(
    ("default", "allowed"),
    [
        ("omega-unapproved", ("omega-approved",)),
        ("omega-approved", ()),
        ("", ("omega-approved",)),
        ("omega-approved", ("omega-other",)),
        ("omega-approved", ("",)),
    ],
)
def test_no_silent_fallback_or_provider_call_when_policy_unverified(
    monkeypatch, default, allowed
):
    monkeypatch.setenv("OPENAI_API_KEY", "OMEGA_TEST_ONLY_NOT_REAL")
    monkeypatch.setattr(server, "DEFAULT_MODEL", default)
    monkeypatch.setattr(server, "ALLOWED_MODELS", allowed)
    called = []

    def forbid_urlopen(*args, **kwargs):
        called.append(True)
        raise AssertionError("Unapproved model must not reach an external provider")

    monkeypatch.setattr(server.urllib.request, "urlopen", forbid_urlopen)
    with pytest.raises(RuntimeError, match="^MODEL_POLICY_DENIED$"):
        server.call_openai("synthetic request", [])
    assert called == []


def test_approved_model_is_sent_unchanged_only_to_mock_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "OMEGA_TEST_ONLY_NOT_REAL")
    monkeypatch.setattr(server, "DEFAULT_MODEL", "omega-approved")
    monkeypatch.setattr(server, "ALLOWED_MODELS", ("omega-approved", "omega-other"))
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"output_text":"synthetic reply"}'

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    reply, model = server.call_openai("synthetic request", [])
    assert reply == "synthetic reply"
    assert model == "omega-approved"
    assert captured["body"]["model"] == "omega-approved"
    assert captured["body"]["store"] is False


def test_missing_provider_key_fails_before_model_selection(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(server, "DEFAULT_MODEL", "")
    monkeypatch.setattr(server, "ALLOWED_MODELS", ())
    with pytest.raises(RuntimeError, match="^PROVIDER_NOT_CONFIGURED$"):
        server.call_openai("synthetic", [])
