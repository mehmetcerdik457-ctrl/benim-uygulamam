"""Only synthetic audit data and temporary directories. No live key or account."""

from datetime import datetime, timezone
from secrets import token_bytes
import sqlite3

import pytest

from omega_mvi.security.audit_fixture import (
    AuditAnchor, DB_NAME, SENTINEL_CONTENT, SENTINEL_NAME, FixtureAuditLedger,
)
from omega_mvi.security.offline_contract import SafeAuditEvent, SecurityDenied

NOW = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)
WRITER = "synthetic.audit"
TEST_EVENT = SafeAuditEvent("secret_use", "synthetic.inventory", "denied")


@pytest.fixture
def marked_folder(tmp_path):
    (tmp_path / SENTINEL_NAME).write_text(SENTINEL_CONTENT, encoding="ascii")
    return tmp_path


def test_025_synthetic_audit_persists_and_anchor_verifies_after_reopen(marked_folder):
    key = token_bytes(32)  # fixture key: in process only, never disk/log
    first = FixtureAuditLedger(marked_folder, key, create=True)
    a1 = first.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW)
    a2 = first.append(writer=WRITER,
                      event=SafeAuditEvent("access_revoke", "synthetic.inventory", "revoked"),
                      occurred_at=NOW)
    assert a1.sequence == 1 and a2.sequence == 2 and a1.mac_hex != a2.mac_hex
    first.close()

    db = marked_folder / DB_NAME
    assert db.exists() and db.stat().st_mode & 0o077 == 0
    reopened = FixtureAuditLedger(marked_folder, key)
    assert reopened.verify(expected_anchor=a2) == a2
    assert reopened.verify(expected_anchor=a1) == a2
    rows = reopened._db.execute("SELECT * FROM audit_events").fetchall()
    assert len(rows) == 2
    assert all(len(row) == 6 for row in rows)
    assert "token" not in str(rows).lower()
    assert "password" not in str(rows).lower()
    assert "private key" not in str(rows).lower()
    reopened.close()


def test_025_writer_auth_is_fixture_only_and_fixed_schema(marked_folder):
    ledger = FixtureAuditLedger(marked_folder, token_bytes(32), create=True)
    with pytest.raises(SecurityDenied, match="SERVICE_SCOPE_DENIED"):
        ledger.append(writer="synthetic.inventory", event=TEST_EVENT, occurred_at=NOW)
    with pytest.raises(SecurityDenied, match="AUDIT_FIXED_SCHEMA_REQUIRED"):
        ledger.append(writer=WRITER, event={"token": "synthetic-secret"}, occurred_at=NOW)
    with pytest.raises(SecurityDenied, match="AUDIT_UTC_REQUIRED"):
        ledger.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW.replace(tzinfo=None))
    with pytest.raises(SecurityDenied, match="AUDIT_SERVICE_DENIED"):
        ledger.append(writer=WRITER,
                      event=SafeAuditEvent("secret_use", "untrusted-bearer-token", "denied"),
                      occurred_at=NOW)
    assert ledger.verify().sequence == 0
    ledger.close()


def test_025_triggers_reject_update_delete(marked_folder):
    ledger = FixtureAuditLedger(marked_folder, token_bytes(32), create=True)
    original = ledger.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW)
    with pytest.raises(sqlite3.IntegrityError):
        ledger._db.execute("UPDATE audit_events SET outcome='allowed_fixture' WHERE seq=1")
    with pytest.raises(sqlite3.IntegrityError):
        ledger._db.execute("DELETE FROM audit_events WHERE seq=1")
    assert ledger.verify(expected_anchor=original) == original
    ledger.close()


def test_025_mac_detects_privileged_db_tampering(marked_folder):
    key = token_bytes(32)
    ledger = FixtureAuditLedger(marked_folder, key, create=True)
    anchor = ledger.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW)
    ledger.close()
    db = sqlite3.connect(marked_folder / DB_NAME)
    db.execute("DROP TRIGGER audit_no_update")
    db.execute("UPDATE audit_events SET outcome='allowed_fixture' WHERE seq=1")
    db.commit()
    db.close()
    with pytest.raises(SecurityDenied, match="AUDIT_UNAVAILABLE_OR_TAMPERED"):
        FixtureAuditLedger(marked_folder, key)
    # An attacker with privileged DB access can remove triggers; the external
    # HMAC key and witness anchor must remain outside that DB.


def test_025_external_anchor_detects_complete_tail_truncation(marked_folder):
    key = token_bytes(32)
    ledger = FixtureAuditLedger(marked_folder, key, create=True)
    ledger.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW)
    anchor = ledger.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW)
    ledger.close()
    db = sqlite3.connect(marked_folder / DB_NAME)
    db.execute("DROP TRIGGER audit_no_delete")
    db.execute("DELETE FROM audit_events WHERE seq=2")
    db.execute("""CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events
                  BEGIN SELECT RAISE(ABORT,'IMMUTABLE_AUDIT'); END;""")
    db.commit()
    db.close()
    ledger = FixtureAuditLedger(marked_folder, key)
    assert ledger.verify().sequence == 1  # chain alone CANNOT detect truncation!
    with pytest.raises(SecurityDenied, match="AUDIT_EXTERNAL_ANCHOR_MISMATCH"):
        ledger.verify(expected_anchor=anchor)
    ledger.close()


def test_025_wrong_key_or_wrong_anchor_fails_closed(marked_folder):
    key = token_bytes(32)
    ledger = FixtureAuditLedger(marked_folder, key, create=True)
    anchor = ledger.append(writer=WRITER, event=TEST_EVENT, occurred_at=NOW)
    with pytest.raises(SecurityDenied, match="AUDIT_EXTERNAL_ANCHOR_MISMATCH"):
        ledger.verify(expected_anchor=AuditAnchor(anchor.sequence, "0" * 64))
    ledger.close()
    with pytest.raises(SecurityDenied, match="AUDIT_UNAVAILABLE_OR_TAMPERED"):
        FixtureAuditLedger(marked_folder, token_bytes(32))


def test_025_unmarked_or_wrong_sentinel_and_existing_file_denied(tmp_path, marked_folder):
    # This test exercises the guard, never writes in unmarked paths.
    plain = tmp_path / "nonfixture"
    plain.mkdir()
    with pytest.raises(SecurityDenied, match="SYNTHETIC_AUDIT_SENTINEL_REQUIRED"):
        FixtureAuditLedger(plain, token_bytes(32), create=True)
    ledger = FixtureAuditLedger(marked_folder, token_bytes(32), create=True)
    ledger.close()
    with pytest.raises(SecurityDenied, match="AUDIT_ALREADY_EXISTS"):
        FixtureAuditLedger(marked_folder, token_bytes(32), create=True)
    (marked_folder / SENTINEL_NAME).write_text("wrong marker", encoding="ascii")
    with pytest.raises(SecurityDenied, match="SYNTHETIC_AUDIT_SENTINEL_REQUIRED"):
        FixtureAuditLedger(marked_folder, token_bytes(32))
