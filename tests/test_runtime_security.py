import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runtime_security


def basic(user: str, password: str) -> str:
    raw = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + raw


def test_owner_auth_fails_closed_without_credentials(monkeypatch):
    monkeypatch.delenv("OWNER_BASIC_USER", raising=False)
    monkeypatch.delenv("OWNER_BASIC_PASSWORD", raising=False)
    assert runtime_security.owner_auth_configured() is False
    assert runtime_security.owner_authorized(basic("x", "y")) is False


def test_owner_auth_accepts_only_exact_credentials(monkeypatch):
    monkeypatch.setenv("OWNER_BASIC_USER", "mehmet")
    monkeypatch.setenv("OWNER_BASIC_PASSWORD", "test-only-password")
    assert runtime_security.owner_auth_configured() is True
    assert runtime_security.owner_authorized(basic("mehmet", "test-only-password"))
    assert not runtime_security.owner_authorized(basic("mehmet", "wrong"))
    assert not runtime_security.owner_authorized(None)


def test_backend_proxy_token(monkeypatch):
    monkeypatch.delenv("AI_BACKEND_PROXY_TOKEN", raising=False)
    assert runtime_security.backend_proxy_token() == ""
    monkeypatch.setenv("AI_BACKEND_PROXY_TOKEN", "internal-test-token")
    assert runtime_security.backend_proxy_token() == "internal-test-token"
