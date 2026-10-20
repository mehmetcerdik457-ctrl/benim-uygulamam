"""S10 live-public AST UI boundary — uses true local module bytes as fixture.

NOT an Owner IdP, physical device, production search ACL or 0.1.4-dev acceptance.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from omega_mvi.inspection.source_index import index_public_sources


def test_public_ast_source_index_browser_contract(tmp_path):
    node = shutil.which("node")
    assert node, "Node.js required: cannot skip the UI security gate"
    fixture = index_public_sources()
    assert fixture["files_indexed"] == 5
    fixture_file = tmp_path / "public-source-index.json"
    fixture_file.write_text(json.dumps(fixture, sort_keys=True), encoding="utf-8")
    script = Path(__file__).with_name("ui_public_ast_index_contract.cjs")
    env = {**os.environ, "OMEGA_PUBLIC_AST_FIXTURE": str(fixture_file)}
    result = subprocess.run(
        [node, "--test", str(script)], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_public_index_endpoint_does_not_turn_into_owner_authority(monkeypatch):
    from fastapi.testclient import TestClient
    sys.path.insert(0, str(ROOT))
    from app.main import app

    client = TestClient(app)
    before = client.get("/api/demo/source-index")
    after = client.get("/api/demo/source-index", headers={
        "Authorization": "Bearer SYNTHETIC_NOT_REAL",
        "X-Owner": "owner",
        "X-Role": "admin"
    })
    assert before.status_code == 200
    assert after.status_code == 200
    assert before.headers["cache-control"] == "no-store"
    assert before.headers["x-content-type-options"] == "nosniff"
    assert after.headers["cache-control"] == "no-store"
    assert after.json() == before.json()
    assert after.json()["authenticated_owner"] is False
    assert after.json()["production_ready"] is False
    assert after.json()["acceptance"] == "NOT_ACCEPTED"
    assert client.post("/api/execute", json={"target": "synthetic"}).status_code == 403


def test_public_index_read_error_fails_closed_with_generic_message(monkeypatch):
    """Raw paths, source snippets and operating-system errors never reach UI."""
    from fastapi.testclient import TestClient
    from omega_mvi.inspection import source_index
    sys.path.insert(0, str(ROOT))
    from app.main import app

    def unavailable():
        raise source_index.SourceIndexError("PRIVATE_SOURCE_SENTINEL")
    monkeypatch.setattr(source_index, "index_public_sources", unavailable)
    result = TestClient(app).get("/api/demo/source-index")
    assert result.status_code == 503
    assert result.json() == {"detail": "PUBLIC_SOURCE_INDEX_UNAVAILABLE"}
    assert "PRIVATE_SOURCE_SENTINEL" not in result.text
