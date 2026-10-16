"""Purely offline contracts: every provider path is synthetic and mocked."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import omega_provider_smoke as probe


def fake(reply="MEHMET_LIVE_OK", model="synthetic-allowed"):
    calls = []

    def generate(prompt, attachments, *, max_output_tokens=None):
        calls.append((prompt, attachments, max_output_tokens))
        return reply, model

    backend = SimpleNamespace(
        OPENAI_URL="https://api.openai.com/v1/responses",
        configured=lambda: True,
        proxy_configured=lambda: True,
        ALLOWED_MODELS=("synthetic-allowed",),
        DEFAULT_MODEL="synthetic-allowed",
        MAX_OUTPUT_TOKENS=2048,
        call_openai=generate,
    )
    return backend, calls


def approval():
    return {
        "OMEGA_SINGLE_PROVIDER_PROBE_APPROVED": "YES",
        "OMEGA_SINGLE_PROVIDER_PROBE_MODEL": "synthetic-allowed",
    }


def test_offline_pass_never_calls_provider(capsys):
    backend, called = fake()
    assert probe.execute("offline", backend, {}) == 0
    assert called == []
    assert "NO_MODEL_REQUEST" in capsys.readouterr().out


def test_missing_config_denies_without_generation():
    backend, called = fake()
    backend.configured = lambda: False
    assert probe.execute("offline", backend, {}) == 2
    assert called == []


def test_empty_allowlist_denies_without_generation():
    backend, called = fake()
    backend.ALLOWED_MODELS = ()
    assert probe.execute("offline", backend, {}) == 2
    assert called == []


def test_live_missing_approval_denied():
    backend, called = fake()
    assert probe.execute("live", backend, {}) == 2
    assert called == []


def test_live_different_model_denied():
    backend, called = fake()
    ctx = approval()
    ctx["OMEGA_SINGLE_PROVIDER_PROBE_MODEL"] = "unapproved"
    assert probe.execute("live", backend, ctx) == 2
    assert called == []


@pytest.mark.parametrize("name", (
    "CI", "GITHUB_ACTIONS", "RAILWAY_ENVIRONMENT_ID",
    "RAILWAY_SERVICE_ID", "RAILWAY_PROJECT_ID",
))
def test_live_is_denied_inside_ci_or_hosted_railway(name, capsys):
    backend, called = fake()
    ctx = approval()
    ctx[name] = "1"
    assert probe.execute("live", backend, ctx) == 2
    assert called == []
    assert "HOSTED_RUNTIME_DENIED" in capsys.readouterr().out


def test_live_one_bounded_fake_call_only(capsys):
    backend, called = fake()
    previous_limit = backend.MAX_OUTPUT_TOKENS
    assert probe.execute("live", backend, approval()) == 0
    assert called == [(probe.PROMPT, [], 16)]
    assert backend.MAX_OUTPUT_TOKENS == previous_limit
    assert "PASS_SINGLE_LIVE_REQUEST" in capsys.readouterr().out


def test_live_response_mismatch_fails_and_never_prints_reply(capsys):
    backend, called = fake(reply="PRIVATE_RESPONSE_MUST_NOT_LEAK")
    assert probe.execute("live", backend, approval()) == 1
    out = capsys.readouterr().out
    assert "MISMATCH" in out and "PRIVATE_RESPONSE_MUST_NOT_LEAK" not in out
    assert called == [(probe.PROMPT, [], 16)]


def test_live_wrong_model_fails():
    backend, called = fake(model="wrong")
    assert probe.execute("live", backend, approval()) == 1
    assert len(called) == 1


def test_live_exception_sanitized_and_default_intact(capsys):
    backend, called = fake()

    def forbidden(*args, **kwargs):
        raise RuntimeError("FAKE_KEY_MUST_NOT_APPEAR")

    backend.call_openai = forbidden
    assert probe.execute("live", backend, approval()) == 1
    assert "FAKE_KEY_MUST_NOT_APPEAR" not in capsys.readouterr().out
    assert backend.MAX_OUTPUT_TOKENS == 2048
    assert called == []


def test_live_missing_adapter_denied_before_call():
    backend, called = fake()
    backend.call_openai = None
    assert probe.execute("live", backend, approval()) == 2
    assert called == []


def test_offline_never_calls_faulting_backend():
    backend, called = fake()
    backend.call_openai = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run"))
    assert probe.execute("offline", backend, {}) == 0
    assert called == []


def test_exact_reply_parser_is_strict():
    assert probe.exact_reply_ok("MEHMET_LIVE_OK")
    assert not probe.exact_reply_ok("WRONG")
    assert not probe.exact_reply_ok(None)
    assert not probe.exact_reply_ok(True)
