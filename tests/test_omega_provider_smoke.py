"""Purely offline contracts. Never contacts a real provider or accesses a key."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import omega_provider_smoke as probe


def fake(reply="MEHMET_LIVE_OK", model="synthetic-allowed"):
    called = []
    def generate(prompt, attachments):
        called.append((prompt, attachments))
        return reply, model
    b = SimpleNamespace(
        OPENAI_URL="https://api.openai.com/v1/responses",
        configured=lambda: True,
        proxy_configured=lambda: True,
        ALLOWED_MODELS=("synthetic-allowed",),
        DEFAULT_MODEL="synthetic-allowed",
        MAX_OUTPUT_TOKENS=2048,
        call_openai=generate,
    )
    return b, called


def test_offline_pass_never_calls_provider(capsys):
    backend, called = fake()
    assert probe.execute("offline", backend, {}) == 0
    assert called == []
    assert "NO_MODEL_REQUEST" in capsys.readouterr().out


def test_missing_configuration_fails_closed_without_generation(capsys):
    backend, called = fake()
    backend.configured = lambda: False
    assert probe.execute("offline", backend, {}) == 2
    assert called == []
    assert "CONFIGURATION_DENIED" in capsys.readouterr().out


def test_allowlist_absent_denies(capsys):
    backend, called = fake()
    backend.ALLOWED_MODELS = tuple()
    assert probe.execute("offline", backend, {}) == 2
    assert called == []


def test_live_requires_explicit_separate_approval(capsys):
    backend, called = fake()
    assert probe.execute("live", backend, {}) == 2
    assert called == []
    assert "APPROVAL" in capsys.readouterr().out


def test_live_requires_exact_allowlisted_model(capsys):
    backend, called = fake()
    assert probe.execute("live", backend, {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED":"YES", "OMEGA_SINGLE_PROVIDER_PROBE_MODEL":"different"}) == 2
    assert called == []


def test_live_even_with_approval_fails_closed_without_adapter(capsys):
    backend, called = fake()
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED": "YES",
           "OMEGA_SINGLE_PROVIDER_PROBE_MODEL": "synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 2
    assert called == []
    assert "SAFE_LIVE_ADAPTER_NOT_IMPLEMENTED" in capsys.readouterr().out


def test_live_never_mutates_global_output_limit(capsys):
    backend, called = fake()
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED": "YES",
           "OMEGA_SINGLE_PROVIDER_PROBE_MODEL": "synthetic-allowed"}
    original = backend.MAX_OUTPUT_TOKENS
    assert probe.execute("live", backend, ctx) == 2
    assert backend.MAX_OUTPUT_TOKENS == original
    assert called == []


def test_live_does_not_invoke_faulting_backend(capsys):
    backend, called = fake()
    def boom(*args):
        raise RuntimeError("SECRET_PROVIDER_DETAIL_NOT_FOR_LOGS")
    backend.call_openai = boom
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED": "YES",
           "OMEGA_SINGLE_PROVIDER_PROBE_MODEL": "synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 2
    assert "SECRET_PROVIDER_DETAIL_NOT_FOR_LOGS" not in capsys.readouterr().out
    assert called == []


def test_offline_never_calls_faulting_backend(capsys):
    backend, called = fake()
    backend.call_openai = lambda *args: (_ for _ in ()).throw(ValueError("must not run"))
    assert probe.execute("offline", backend, {}) == 0
    assert called == []


def test_exact_reply_parser_is_strict():
    assert probe.exact_reply_ok("MEHMET_LIVE_OK")
    assert not probe.exact_reply_ok("not the expected answer")
    assert not probe.exact_reply_ok(None)
