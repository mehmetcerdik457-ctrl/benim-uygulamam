import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import pytest
from payouts.ledger import LedgerConflict, initialize, record_external_payout, record_financial_line, reconcile_period

def test_idempotent_financial_import_and_external_reconciliation(tmp_path):
    db = tmp_path / "ledger.sqlite"
    initialize(db)
    args = dict(report_id="earnings-2026-10", period="2026-10", line_id="row-001",
                transaction_type="charge", currency="TRY", net_minor=125000)
    assert record_financial_line(db, **args) is True
    assert record_financial_line(db, **args) is False
    assert record_external_payout(db, payout_reference="google-payout-2026-11",
        period="2026-10", currency="TRY", amount_minor=125000, state="paid") is True
    result = reconcile_period(db, period="2026-10", currency="TRY")
    assert result["variance_minor"] == 0
    assert result["bank_transfer_initiated"] is False
    assert result["bank_details_stored"] is False

def test_replay_with_changed_payload_is_rejected(tmp_path):
    db = tmp_path / "ledger.sqlite"
    initialize(db)
    base = dict(report_id="r1", period="2026-10", line_id="l1",
                transaction_type="charge", currency="TRY", net_minor=100)
    record_financial_line(db, **base)
    with pytest.raises(LedgerConflict):
        record_financial_line(db, **{**base, "net_minor": 101})

def test_invalid_currency_or_state_is_rejected(tmp_path):
    db = tmp_path / "ledger.sqlite"
    initialize(db)
    with pytest.raises(ValueError):
        record_financial_line(db, report_id="r1", period="2026-10", line_id="l1",
            transaction_type="charge", currency="TL", net_minor=100)
    with pytest.raises(ValueError):
        record_external_payout(db, payout_reference="p1", period="2026-10",
            currency="TRY", amount_minor=100, state="execute_transfer")
