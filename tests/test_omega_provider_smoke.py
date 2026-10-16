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


def test_live_exact_match_one_call(capsys):
    backend, called = fake()
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED":"YES", "OMEGA_SINGLE_PROVIDER_PROBE_MODEL":"synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 0
    assert len(called) == 1
    assert called[0][0] == probe.PROMPT
    assert backend.MAX_OUTPUT_TOKENS == 2048
    assert "PASS_SINGLE_LIVE_REQUEST" in capsys.readouterr().out


def test_live_mismatch_fails_nonzero_and_doesnt_print_reply(capsys):
    backend, called = fake(reply="WRONG_SECRET_LIKE_RESPONSE")
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED":"YES", "OMEGA_SINGLE_PROVIDER_PROBE_MODEL":"synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 1
    out = capsys.readouterr().out
    assert "MISMATCH" in out
    assert "WRONG_SECRET_LIKE_RESPONSE" not in out
    assert len(called) == 1
    assert backend.MAX_OUTPUT_TOKENS == 2048


def test_live_wrong_returned_model_fails_nonzero(capsys):
    backend, _ = fake(model="other-provider")
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED":"YES", "OMEGA_SINGLE_PROVIDER_PROBE_MODEL":"synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 1
    assert "MISMATCH" in capsys.readouterr().out


def test_live_provider_exception_is_sanitized_and_limits_restored(capsys):
    backend, called = fake()
    def boom(prompt, attachments):
        raise RuntimeError("SECRET_PROVIDER_DETAIL_NOT_FOR_LOGS")
    backend.call_openai = boom
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED":"YES", "OMEGA_SINGLE_PROVIDER_PROBE_MODEL":"synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 1
    assert "SECRET_PROVIDER_DETAIL_NOT_FOR_LOGS" not in capsys.readouterr().out
    assert backend.MAX_OUTPUT_TOKENS == 2048


def test_null_response_fails_nonzero(capsys):
    backend, _ = fake(reply=None)
    ctx = {"OMEGA_SINGLE_PROVIDER_PROBE_APPROVED":"YES", "OMEGA_SINGLE_PROVIDER_PROBE_MODEL":"synthetic-allowed"}
    assert probe.execute("live", backend, ctx) == 1
