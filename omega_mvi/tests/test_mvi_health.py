"""Offline contract tests for the isolated dummy FastAPI application."""
import os
import sys
from pathlib import Path

import pytest
pytest.importorskip("fastapi", reason="install omega_mvi/requirements-test.txt")
pytest.importorskip("httpx", reason="install omega_mvi/requirements-test.txt")
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app

client = TestClient(app)


def test_health_paths_report_demo_only():
    for path in ("/health", "/api/health"):
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["mode"] == "mock"
        assert data["production_ready"] is False
        assert data["external_api_enabled"] is False
        assert data["owner_hardware"] == "UNKNOWN"


def test_all_side_effects_fail_closed():
    for endpoint in ("/api/execute", "/api/chat"):
        res = client.post(endpoint, json={"action": "delete", "resource": "not-real"})
        assert res.status_code == 403
        assert "DENIED" in res.json()["detail"]


def test_no_secret_environment_reflection(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "FAKE_FIXTURE_DO_NOT_USE")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "FAKE_FIXTURE_DO_NOT_USE" not in response.text
    assert "OPENAI_API_KEY" not in response.text


def test_not_ready_for_production():
    res = client.get("/api/readiness")
    assert res.status_code == 200
    assert res.json()["production_ready"] is False


def test_openapi_not_exposed():
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
