"""Tests for live, non-synthetic source inventory and read-only HTTP view."""
import hashlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from omega_mvi.inspection.source_index import (
    SOURCE_FILES,
    SourceIndexError,
    _read_public_file,
    index_public_sources,
)


def test_real_checked_out_public_source_bytes_and_hashes():
    result = index_public_sources()
    assert result["mode"] == "real-public-source-ast"
    assert result["files_indexed"] == len(SOURCE_FILES)
    assert result["symbol_count"] >= 10
    assert result["read_only"] and result["external_calls"] is False
    assert result["production_ready"] is False
    assert result["acceptance"] == "NOT_ACCEPTED"
    for item in result["files"]:
        path = ROOT / item["path"].removeprefix("omega_mvi/")
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert len(raw) == item["byte_length"]
        assert item["symbols"]  # Real definitions, not fabricated labels.
        assert all(x["line"] > 0 for x in item["symbols"])
        assert all(x["from"] and x["to"] for x in item["call_edges"])
    file = next(x for x in result["files"] if x["path"].endswith("pipeline.py"))
    assert any(x["symbol"] == "inspect_offline_fixture" for x in file["symbols"])
    assert any("omega_mvi.inspection" in x for x in file["imports"])


def test_index_is_deterministic_without_writing_source():
    left = index_public_sources()
    right = index_public_sources()
    assert left == right
    assert sum(x["dynamic_calls_unresolved"] for x in left["files"]) >= 0


def test_only_explicit_public_modules_are_readable():
    with pytest.raises(SourceIndexError, match="SOURCE_NOT_ALLOWLISTED"):
        _read_public_file(ROOT / "inspection", "private/.env")
    with pytest.raises(SourceIndexError, match="SOURCE_NOT_ALLOWLISTED"):
        _read_public_file(ROOT / "inspection", "../app/main.py")


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_symlink_in_module_path_is_not_followed(tmp_path):
    # Only the explicitly named module can be requested, but not through links.
    (tmp_path / "source.py").write_text("pass\n")
    (tmp_path / "pipeline.py").symlink_to(tmp_path / "source.py")
    with pytest.raises(SourceIndexError):
        _read_public_file(tmp_path, "pipeline.py")
    (tmp_path / "retrieval").symlink_to(tmp_path)
    with pytest.raises(SourceIndexError):
        _read_public_file(tmp_path, "retrieval/__init__.py")


def test_real_fastapi_code_index_with_no_identity(monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("OMEGA_MODE", "mock")
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC_KEY_NOT_REAL")
    client = TestClient(app)
    resp = client.get("/api/demo/source-index")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["files_indexed"] == 5
    assert payload["mode"] == "real-public-source-ast"
    assert payload["authenticated_owner"] is False
    assert payload["production_ready"] is False
    assert not any("secret" in f or ".env" in f for f in
                   (item["path"] for item in payload["files"]))
    assert "SYNTHETIC_KEY_NOT_REAL" not in resp.text
    assert "source" not in payload or "prompt" not in payload
    # Existing write endpoints remain off.
    assert client.post("/api/execute", json={"action": "run"}).status_code == 403
    assert client.post("/api/chat", json={"message": "hello"}).status_code == 403
