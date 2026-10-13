"""OMEGA-029 fixture-only SQLite -> AES-GCM -> SQLite recovery exercise.

No production database or backup path is accepted. Both source and restore
targets MUST be in-memory SQLite and contain the explicit synthetic sentinel.
The encrypted envelope can be copied ONLY by the caller into a disposable test
directory. Never handles legacy encrypted backups or recovery secrets.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from secrets import compare_digest

from .offline_contract import (
    FIXTURE_DATA_PREFIX, SecurityDenied, encrypt_synthetic_backup,
    restore_synthetic_backup,
)

DB_SENTINEL = "OMEGA-SYNTHETIC-MEMORY-DB-V1"
MAX_RECORDS = 16


@dataclass(frozen=True)
class SyntheticBackup:
    version: int
    envelope: bytes
    sha256_hex: str


def _one_memory_database(conn: sqlite3.Connection):
    if type(conn) is not sqlite3.Connection:
        raise SecurityDenied("RECOVERY_MEMORY_SQLITE_ONLY")
    try:
        databases = conn.execute("PRAGMA database_list").fetchall()
        # An attached :memory: schema (empty filename) must NOT bypass isolation.
        if (len(databases) != 1 or databases[0][1] != "main"
                or databases[0][2] != ""):
            raise SecurityDenied("RECOVERY_MEMORY_SQLITE_ONLY")
    except sqlite3.Error:
        raise SecurityDenied("RECOVERY_MEMORY_SQLITE_ONLY") from None


def _memory_guard(conn: sqlite3.Connection):
    _one_memory_database(conn)
    try:
        objects = conn.execute(
            "SELECT type,name FROM main.sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if set(objects) != {
            ("table", "omega_fixture_sentinel"),
            ("table", "omega_fixture_records"),
        } or len(objects) != 2:
            raise SecurityDenied("RECOVERY_UNEXPECTED_SCHEMA")
        # Reject altered columns/constraints even when expected table names exist.
        required = {
            "omega_fixture_sentinel": [("id", "INTEGER", 0, 1), ("marker", "TEXT", 1, 0)],
            "omega_fixture_records": [("id", "TEXT", 0, 1), ("value", "TEXT", 1, 0)],
        }
        for table, expected in required.items():
            columns = conn.execute(f"PRAGMA main.table_info({table})").fetchall()
            if [(r[1], r[2], r[3], r[5]) for r in columns] != expected:
                raise SecurityDenied("RECOVERY_UNEXPECTED_SCHEMA")
        marker = conn.execute(
            "SELECT marker FROM main.omega_fixture_sentinel WHERE id = 1"
        ).fetchall()
        if marker != [(DB_SENTINEL,)]:
            raise SecurityDenied("RECOVERY_SENTINEL_MISSING")
    except sqlite3.Error:
        raise SecurityDenied("RECOVERY_UNEXPECTED_SCHEMA") from None


def create_memory_fixture(conn: sqlite3.Connection):
    """Called only by test setup; refuses disk-backed and populated databases."""
    _one_memory_database(conn)
    # Do not initialize a database already containing a view, trigger or table.
    existing = [x[0] for x in conn.execute(
        "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    )]
    if existing:
        raise SecurityDenied("RECOVERY_NONEMPTY_DATABASE")
    conn.execute("CREATE TABLE omega_fixture_sentinel (id INTEGER PRIMARY KEY, marker TEXT NOT NULL)")
    conn.execute("INSERT INTO omega_fixture_sentinel(id,marker) VALUES(1,?)", (DB_SENTINEL,))
    conn.execute("CREATE TABLE omega_fixture_records (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.commit()
    _memory_guard(conn)


def _validate_records(rows):
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
        raise SecurityDenied("RECOVERY_NON_SYNTHETIC_PAYLOAD")
    ids = set()
    for row in rows:
        if (not isinstance(row, list) or len(row) != 2
                or any(type(value) is not str for value in row)
                or not row[0].startswith("synthetic-record-")
                or not row[1].startswith("synthetic-data-")
                or len(row[0]) > 80 or len(row[1]) > 200
                or row[0] in ids):
            raise SecurityDenied("RECOVERY_NON_SYNTHETIC_PAYLOAD")
        ids.add(row[0])


def export_memory_fixture(conn: sqlite3.Connection, key: bytes) -> SyntheticBackup:
    _memory_guard(conn)
    try:
        rows = [list(row) for row in conn.execute(
            "SELECT id,value FROM omega_fixture_records ORDER BY id LIMIT ?", (MAX_RECORDS + 1,)
        )]
        _validate_records(rows)
        payload = FIXTURE_DATA_PREFIX + json.dumps(
            rows, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        envelope = encrypt_synthetic_backup(payload, key)
        return SyntheticBackup(1, envelope, hashlib.sha256(envelope).hexdigest())
    except sqlite3.Error:
        raise SecurityDenied("RECOVERY_EXPORT_DENIED") from None


def restore_memory_fixture(conn: sqlite3.Connection, snapshot: SyntheticBackup,
                           key: bytes) -> int:
    _memory_guard(conn)
    if not isinstance(snapshot, SyntheticBackup) or type(snapshot.version) is not int or snapshot.version != 1:
        raise SecurityDenied("RECOVERY_MANIFEST_DENIED")
    if (not isinstance(snapshot.envelope, bytes)
            or type(snapshot.sha256_hex) is not str
            or not compare_digest(hashlib.sha256(snapshot.envelope).hexdigest(),
                                   snapshot.sha256_hex)):
        raise SecurityDenied("RECOVERY_MANIFEST_DENIED")
    decrypted = restore_synthetic_backup(snapshot.envelope, key)
    try:
        rows = json.loads(decrypted[len(FIXTURE_DATA_PREFIX):].decode("ascii"))
        _validate_records(rows)
    except (ValueError, UnicodeError, TypeError):
        raise SecurityDenied("RECOVERY_NON_SYNTHETIC_PAYLOAD") from None

    try:
        if conn.execute("SELECT COUNT(*) FROM omega_fixture_records").fetchone()[0] != 0:
            raise SecurityDenied("RECOVERY_TARGET_NOT_EMPTY")
    except sqlite3.Error:
        raise SecurityDenied("RECOVERY_RESTORE_DENIED") from None
    started = False
    try:
        conn.execute("SAVEPOINT omega_synthetic_restore")
        started = True
        for row_id, value in rows:
            conn.execute("INSERT INTO omega_fixture_records(id,value) VALUES(?,?)", (row_id, value))
        conn.execute("RELEASE SAVEPOINT omega_synthetic_restore")
    except (sqlite3.Error, SecurityDenied):
        if started:
            conn.execute("ROLLBACK TO SAVEPOINT omega_synthetic_restore")
            conn.execute("RELEASE SAVEPOINT omega_synthetic_restore")
        raise SecurityDenied("RECOVERY_RESTORE_DENIED") from None
    return len(rows)
