"""Turkish read-only UI must run without inline JS or cross-site requests."""
from pathlib import Path
import sys
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app

client=TestClient(app)

def test_csp_denies_inline_scripts_and_third_party_assets():
    response=client.get("/")
    assert response.status_code==200
    csp=response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert response.headers["x-frame-options"]=="DENY"
    assert "<script src=\"/assets/dashboard.js\" defer></script>" in response.text
    assert '<link rel="stylesheet" href="/assets/dashboard.css">' in response.text
    assert "<script>" not in response.text and "<style>" not in response.text

def test_fixed_assets_exist_and_render_sensitive_data_only_as_text():
    js=client.get("/assets/dashboard.js")
    css=client.get("/assets/dashboard.css")
    assert js.status_code==200 and css.status_code==200
    assert js.headers["x-content-type-options"]=="nosniff"
    assert js.headers["cross-origin-resource-policy"]=="same-origin"
    assert "textContent" in js.text
    assert "innerHTML" not in js.text
    assert "eval(" not in js.text
    assert "/api/demo/task-status" in js.text
    assert "/api/demo/inspection" in js.text
    assert "createElement" in js.text
    assert "https://" not in js.text and "http://" not in js.text
    assert "credentials:\"omit\"" in js.text
    assert "unsafe-inline" not in css.text

def test_no_runtime_identity_means_denied_and_no_execute(monkeypatch):
    monkeypatch.delenv("OMEGA_DEMO_READS_ENABLED",raising=False)
    assert client.get("/api/demo/task-status").status_code==403
    assert client.post("/api/execute",json={"anything":"synthetic"}).status_code==403
    assert client.post("/api/chat",json={"message":"test"}).status_code==403
    page=client.get("/")
    assert "KABUL EDİLMEDİ" in page.text
