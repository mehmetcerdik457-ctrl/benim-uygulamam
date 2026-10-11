"""Read-only API exercises all four modules in the same app process."""
from fastapi.testclient import TestClient
from app.main import app


def test_four_module_synthetic_api_and_closed_execution():
    client = TestClient(app)
    response = client.get("/api/inspection/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "synthetic-read-only"
    assert body["fixture_only"] is True
    assert body["real_identity_verified"] is False
    assert body["execution_allowed"] is False
    assert body["inventory"]["visibility"] == "public"
    assert "SYNTHETIC FIXTURE" in body["inventory"]["description"]
    assert body["redaction"] == {"applied": True, "source_text_returned": False}
    assert body["retrieval"]["citations"] == [
        "synthetic://omega-fixtures/provenance.md#citations"
    ]
    assert body["retrieval"]["real_documents_indexed"] is False
    assert body["pr_review"]["categories"] == ["security", "authorization"]
    assert body["pr_review"]["advisory_only"] is True
    assert body["pr_review"]["approval_authority"] is False
    assert "offline-demo-placeholder" not in response.text
    assert client.post("/api/execute", json={"action": "run"}).status_code == 403
    assert client.post("/api/chat", json={"prompt": "run"}).status_code == 403


def test_inspection_is_get_only_and_has_no_real_identity_provider():
    client = TestClient(app)
    assert client.post("/api/inspection/demo").status_code == 405
    assert client.get("/api/readiness").json()["production_ready"] is False
