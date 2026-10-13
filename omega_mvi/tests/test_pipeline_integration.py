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


def test_untrusted_public_repository_description_redacted_before_api_output(monkeypatch):
    from omega_mvi.inspection import pipeline
    marker="g"+"hp_"+("Q"*23)  # synthetic canary, never a real credential
    email="fictional.owner"+"@"+"example.invalid"
    fixture=dict(pipeline.PUBLIC_FIXTURE)
    fixture["description"]="Public repo notes: "+marker+" and "+email
    monkeypatch.setattr(pipeline,"PUBLIC_FIXTURE",fixture)
    result=pipeline.inspect_offline_fixture()
    output=str(result)
    assert marker not in output and email not in output
    assert "[REDACTED" in result["repository"]["description"]
    assert result["authority"]=="none"
    assert result["production_ready"] is False

def test_metadata_redaction_failure_is_fail_closed(monkeypatch):
    import pytest
    from omega_mvi.inspection import pipeline
    fixture=dict(pipeline.PUBLIC_FIXTURE)
    fixture["description"]="synthetic description"
    monkeypatch.setattr(pipeline,"PUBLIC_FIXTURE",fixture)
    monkeypatch.setattr(pipeline,"redact_text",lambda _:None)
    with pytest.raises(PermissionError,match="REDACTION_FAILED"):
        pipeline.inspect_offline_fixture()
