"""Cross-module integration is not a surrogate for original PR CI approval."""
from omega_mvi.inspection.pipeline import inspect_offline_fixture
def test_four_modules_integrated_with_sources_redaction_and_zero_authority():
    result=inspect_offline_fixture()
    assert result["mode"]=="synthetic_offline_only"
    assert result["repository"]["visibility"]=="public"
    assert result["redaction_applied"] is True
    assert len(result["sources"])>=1
    assert all(x["ref"].startswith("synthetic://") for x in result["sources"])
    assert any(x["category"]=="authorization" for x in result["review"])
    assert result["authority"]=="none" and result["production_ready"] is False
    assert "synthetic-opaque-value" not in str(result)


def test_untrusted_inventory_description_is_redacted_in_http_demo(monkeypatch):
    from fastapi.testclient import TestClient
    from importlib import import_module
    from omega_mvi.inspection import pipeline

    # The disposable Dockerfile.test copies /omega_mvi/app into /app/app,
    # while a repository checkout imports it as omega_mvi.app.
    try:
        app = import_module("omega_mvi.app.main").app
    except ModuleNotFoundError as exc:
        if exc.name not in ("omega_mvi.app", "omega_mvi.app.main"):
            raise
        app = import_module("app.main").app

    canary = "g" + "hp_" + ("Q" * 23)
    email = "fictional.owner" + "@" + "example.invalid"
    fixture = dict(pipeline.PUBLIC_FIXTURE)
    fixture["description"] = "Untrusted public summary " + canary + " " + email
    monkeypatch.setattr(pipeline, "PUBLIC_FIXTURE", fixture)

    response = TestClient(app).get("/api/demo/inspection")
    assert response.status_code == 200
    body = response.text
    assert canary not in body and email not in body
    payload = response.json()
    assert "[REDACTED" in payload["repository"]["description"]
    assert payload["mode"] == "synthetic_offline_only"
    assert payload["authority"] == "none"
    assert payload["production_ready"] is False


def test_redaction_failure_denies_pipeline_without_exposing_source(monkeypatch):
    from omega_mvi.inspection import pipeline
    import omega_mvi.inspection.github_inventory as inventory
    import pytest

    fixture = dict(pipeline.PUBLIC_FIXTURE)
    fixture["description"] = "synthetic secret payload"
    monkeypatch.setattr(pipeline, "PUBLIC_FIXTURE", fixture)
    monkeypatch.setattr(inventory, "redact_text", lambda _: None)

    with pytest.raises(PermissionError, match="METADATA_REDACTION_FAILED"):
        pipeline.inspect_offline_fixture()
