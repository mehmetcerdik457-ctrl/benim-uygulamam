"""Ledger for imported Play financial rows and externally reported payouts.

Never initiates a bank transfer, stores bank credentials, changes Play Console
settings, or calls a payment provider. Only records and reconciles imported data.
"""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path
from typing import Any

CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
ALLOWED_PAYOUT_STATES = frozenset({"reported", "paid", "failed", "held"})

class LedgerConflict(ValueError):
    """An idempotency key was reused with different financial data."""

def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db

def initialize(db_path: str | Path) -> None:
    with connect(db_path) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS financial_lines (
                id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL CHECK(provider = 'google_play'),
                report_id TEXT NOT NULL,
                period TEXT NOT NULL,
                line_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                currency TEXT NOT NULL,
                net_minor INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, report_id, line_id)
            );
            CREATE TABLE IF NOT EXISTS external_payouts (
                id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL CHECK(provider = 'google_play'),
                payout_reference TEXT NOT NULL UNIQUE,
                period TEXT NOT NULL,
                currency TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('reported','paid','failed','held')),
                source TEXT NOT NULL CHECK(source = 'operator_import'),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

def record_financial_line(db_path: str | Path, *, report_id: str, period: str,
                          line_id: str, transaction_type: str, currency: str,
                          net_minor: int) -> bool:
    """Insert one imported financial row. False means an identical replay."""
    required = (report_id, period, line_id, transaction_type)
    if any(not isinstance(x, str) or not x.strip() for x in required):
        raise ValueError("FINANCIAL_LINE_FIELDS_REQUIRED")
    if not CURRENCY_RE.fullmatch(currency or ""):
        raise ValueError("INVALID_CURRENCY")
    if isinstance(net_minor, bool) or not isinstance(net_minor, int):
        raise ValueError("AMOUNT_MUST_BE_INTEGER_MINOR_UNITS")
    with connect(db_path) as db:
        row = db.execute(
            """SELECT period, transaction_type, currency, net_minor
               FROM financial_lines
               WHERE provider='google_play' AND report_id=? AND line_id=?""",
            (report_id, line_id),
        ).fetchone()
        expected = (period, transaction_type, currency, net_minor)
        if row:
            actual = (row["period"], row["transaction_type"], row["currency"], row["net_minor"])
            if actual != expected:
                raise LedgerConflict("IDEMPOTENCY_KEY_PAYLOAD_MISMATCH")
            return False
        db.execute(
            """INSERT INTO financial_lines
               (provider, report_id, period, line_id, transaction_type, currency, net_minor)
               VALUES ('google_play', ?, ?, ?, ?, ?, ?)""",
            (report_id, period, line_id, transaction_type, currency, net_minor),
        )
    return True

def record_external_payout(db_path: str | Path, *, payout_reference: str,
                           period: str, currency: str, amount_minor: int,
                           state: str) -> bool:
    """Record payout evidence from an external report; does not initiate payout."""
    if not payout_reference or not period:
        raise ValueError("PAYOUT_REFERENCE_AND_PERIOD_REQUIRED")
    if not CURRENCY_RE.fullmatch(currency or ""):
        raise ValueError("INVALID_CURRENCY")
    if state not in ALLOWED_PAYOUT_STATES:
        raise ValueError("INVALID_PAYOUT_STATE")
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise ValueError("AMOUNT_MUST_BE_INTEGER_MINOR_UNITS")
    with connect(db_path) as db:
        row = db.execute(
            "SELECT period, currency, amount_minor, state FROM external_payouts WHERE payout_reference=?",
            (payout_reference,),
        ).fetchone()
        expected = (period, currency, amount_minor, state)
        if row:
            actual = (row["period"], row["currency"], row["amount_minor"], row["state"])
            if actual != expected:
                raise LedgerConflict("PAYOUT_REFERENCE_PAYLOAD_MISMATCH")
            return False
        db.execute(
            """INSERT INTO external_payouts
               (provider, payout_reference, period, currency, amount_minor, state, source)
               VALUES ('google_play', ?, ?, ?, ?, ?, 'operator_import')""",
            (payout_reference, period, currency, amount_minor, state),
        )
    return True

def reconcile_period(db_path: str | Path, *, period: str, currency: str) -> dict[str, Any]:
    """Compare imported net sales rows with externally reported payout evidence."""
    if not period or not CURRENCY_RE.fullmatch(currency or ""):
        raise ValueError("PERIOD_AND_VALID_CURRENCY_REQUIRED")
    with connect(db_path) as db:
        sales = db.execute(
            """SELECT COALESCE(SUM(net_minor), 0) AS total
               FROM financial_lines WHERE provider='google_play' AND period=? AND currency=?""",
            (period, currency),
        ).fetchone()["total"]
        payouts = db.execute(
            """SELECT COALESCE(SUM(amount_minor), 0) AS total
               FROM external_payouts
               WHERE provider='google_play' AND period=? AND currency=? AND state='paid'""",
            (period, currency),
        ).fetchone()["total"]
    return {
        "provider": "google_play", "period": period, "currency": currency,
        "reported_net_minor": int(sales),
        "externally_confirmed_paid_minor": int(payouts),
        "variance_minor": int(sales) - int(payouts),
        "bank_transfer_initiated": False, "bank_details_stored": False,
    }
