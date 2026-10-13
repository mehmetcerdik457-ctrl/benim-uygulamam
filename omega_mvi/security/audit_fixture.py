"""Disposable SQLite/HMAC audit *fixture*, NEVER a production secret audit sink.

Only a directory marked by a synthetic sentinel is permitted. Caller-owned HMAC
key is not serialized. An external (caller-retained) anchor detects truncation;
SQLite triggers alone do not protect against privileged DB writers. No API,
secret provider, job runner or agent calls this fixture.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .offline_contract import SafeAuditEvent, SecurityDenied, check_fixture_scope

SENTINEL_NAME = ".omega-synthetic-audit-sentinel"
SENTINEL_CONTENT = "OMEGA-SYNTHETIC-AUDIT-ONLY-V1"
DB_NAME = "omega-synthetic-audit.sqlite3"
GENESIS = bytes(32)


@dataclass(frozen=True)
class AuditAnchor:
    sequence: int
    mac_hex: str


def _folder_guard(folder: Path) -> Path:
    if (not isinstance(folder, Path) or folder.is_symlink()
            or not folder.is_dir()):
        raise SecurityDenied("SYNTHETIC_AUDIT_DIRECTORY_REQUIRED")
    sentinel = folder / SENTINEL_NAME
    if not sentinel.is_file() or sentinel.is_symlink():
        raise SecurityDenied("SYNTHETIC_AUDIT_SENTINEL_REQUIRED")
    try:
        if sentinel.read_text(encoding="ascii") != SENTINEL_CONTENT:
            raise SecurityDenied("SYNTHETIC_AUDIT_SENTINEL_REQUIRED")
    except (OSError, UnicodeError) as exc:
        raise SecurityDenied("SYNTHETIC_AUDIT_SENTINEL_REQUIRED") from None
    return folder / DB_NAME


def _timestamp(value: datetime) -> int:
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() != timedelta(0)):
        raise SecurityDenied("AUDIT_UTC_REQUIRED")
    return int(value.timestamp())


class FixtureAuditLedger:
    """Local synthetic-only file, with HMAC chain and external anchor verification."""

    def __init__(self, folder: Path, key: bytes, *, create: bool = False,
                 expected_anchor: AuditAnchor | None = None):
        if not isinstance(key, bytes) or len(key) != 32:
            raise SecurityDenied("AUDIT_FIXTURE_KEY_REQUIRED")
        self._key = key  # Never logged, serialized, exported or put in SQLite.
        dbpath = _folder_guard(folder)
        if create:
            try:
                fd = os.open(str(dbpath), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                os.close(fd)
            except FileExistsError as exc:
                raise SecurityDenied("AUDIT_ALREADY_EXISTS") from None
        if not dbpath.is_file() or dbpath.is_symlink():
            raise SecurityDenied("AUDIT_MISSING_OR_UNSAFE")
        mode = dbpath.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise SecurityDenied("AUDIT_FILE_PERMISSIONS_DENIED")
        try:
            self._db = sqlite3.connect(dbpath, isolation_level=None, timeout=3)
            if create:
                self._db.executescript("""
                CREATE TABLE audit_events (
                    seq INTEGER PRIMARY KEY,
                    occurred_at INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    service TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    mac TEXT NOT NULL
                );
                CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events
                    BEGIN SELECT RAISE(ABORT,'IMMUTABLE_AUDIT'); END;
                CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events
                    BEGIN SELECT RAISE(ABORT,'IMMUTABLE_AUDIT'); END;
                """)
            else:
                names = {row[0] for row in self._db.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                )}
                if not {"audit_no_update", "audit_no_delete"}.issubset(names):
                    raise SecurityDenied("AUDIT_TRIGGER_MISSING")
            verified = self.verify(expected_anchor=expected_anchor)
            # Reopening a nonempty DB without an independently retained witness
            # could silently accept tail truncation. Fail closed instead.
            if not create and verified.sequence > 0:
                # An older valid prefix witness cannot detect a truncated tail.
                # Re-open requires the exact independently retained latest tip.
                if (expected_anchor is None
                        or expected_anchor.sequence != verified.sequence
                        or not hmac.compare_digest(expected_anchor.mac_hex, verified.mac_hex)):
                    raise SecurityDenied("AUDIT_LATEST_ANCHOR_REQUIRED")
        except (sqlite3.Error, SecurityDenied) as exc:
            self._db.close()
            raise SecurityDenied("AUDIT_UNAVAILABLE_OR_TAMPERED") from None

    def close(self):
        self._db.close()

    def _read_verified(self):
        previous = GENESIS
        seq_seen = 0
        anchors = {}
        try:
            rows = self._db.execute(
                "SELECT seq, occurred_at, kind, service, outcome, mac FROM audit_events ORDER BY seq"
            )
            for seq, stamp, kind, service, outcome, mac in rows:
                if type(seq) is not int or seq != seq_seen + 1 or type(stamp) is not int:
                    raise SecurityDenied("AUDIT_CHAIN_INVALID")
                SafeAuditEvent(kind, service, outcome).as_record()
                if type(mac) is not str or len(mac) != 64:
                    raise SecurityDenied("AUDIT_CHAIN_INVALID")
                signed = json.dumps([seq, stamp, kind, service, outcome],
                                    separators=(",", ":"), ensure_ascii=True).encode("ascii")
                expected = hmac.new(self._key, previous + signed, hashlib.sha256).digest()
                if not hmac.compare_digest(mac, expected.hex()):
                    raise SecurityDenied("AUDIT_CHAIN_INVALID")
                previous, seq_seen = expected, seq
                anchors[seq] = mac
        except (sqlite3.Error, TypeError, ValueError, UnicodeError) as exc:
            raise SecurityDenied("AUDIT_CHAIN_INVALID") from None
        return seq_seen, previous.hex(), anchors

    def verify(self, *, expected_anchor: AuditAnchor | None = None) -> AuditAnchor:
        count, last_mac, seen = self._read_verified()
        if expected_anchor is not None:
            if (not isinstance(expected_anchor, AuditAnchor)
                    or type(expected_anchor.sequence) is not int
                    or expected_anchor.sequence < 1
                    or type(expected_anchor.mac_hex) is not str
                    or not hmac.compare_digest(
                        seen.get(expected_anchor.sequence, ""), expected_anchor.mac_hex
                    )):
                raise SecurityDenied("AUDIT_EXTERNAL_ANCHOR_MISMATCH")
        return AuditAnchor(count, last_mac)

    def append(self, *, writer: str, event: SafeAuditEvent,
               occurred_at: datetime) -> AuditAnchor:
        # Fixture writer name is caller-supplied, NOT live workload authentication.
        check_fixture_scope(writer, "audit:append")
        if not isinstance(event, SafeAuditEvent):
            raise SecurityDenied("AUDIT_FIXED_SCHEMA_REQUIRED")
        record = event.as_record()
        stamp = _timestamp(occurred_at)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            sequence, prior_mac, _ = self._read_verified()
            seq = sequence + 1
            payload = json.dumps(
                [seq, stamp, record["kind"], record["service"], record["outcome"]],
                separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
            mac = hmac.new(self._key, bytes.fromhex(prior_mac) + payload,
                           hashlib.sha256).hexdigest()
            self._db.execute(
                "INSERT INTO audit_events(seq, occurred_at, kind, service, outcome, mac)"
                " VALUES(?,?,?,?,?,?)",
                (seq, stamp, record["kind"], record["service"], record["outcome"], mac)
            )
            self._db.execute("COMMIT")
            return AuditAnchor(seq, mac)
        except (sqlite3.Error, SecurityDenied, ValueError) as exc:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise SecurityDenied("AUDIT_WRITE_DENIED") from None
