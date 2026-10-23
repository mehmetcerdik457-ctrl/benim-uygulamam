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
