"""OMEGA-029: an attached in-memory database is NOT an isolated fixture.

SQLite PRAGMA database_list shows an empty filename for each attached ':memory:'
database. A guard checking file paths only therefore misses added database schemas.
All fixtures and payloads here are synthetic; no live or owner data is accessed.
"""
import sqlite3
from secrets import token_bytes

import pytest

from omega_mvi.security.offline_contract import SecurityDenied
from omega_mvi.security.recovery_fixture import (
    create_memory_fixture, export_memory_fixture, restore_memory_fixture,
)


def _fixture():
    db = sqlite3.connect(":memory:")
    create_memory_fixture(db)
    return db


def test_create_denies_attached_second_in_memory_database_before_schema_write():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("ATTACH DATABASE ':memory:' AS additional")
        assert len(conn.execute("PRAGMA database_list").fetchall()) == 2
        with pytest.raises(SecurityDenied, match="RECOVERY_MEMORY_SQLITE_ONLY"):
            create_memory_fixture(conn)
        assert conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 0
    finally:
        conn.close()


def test_export_denies_attached_in_memory_database_before_encryption():
    conn = _fixture()
    try:
        conn.execute("ATTACH DATABASE ':memory:' AS additional")
        with pytest.raises(SecurityDenied, match="RECOVERY_MEMORY_SQLITE_ONLY"):
            export_memory_fixture(conn, token_bytes(32))
    finally:
        conn.close()


def test_restore_denies_attached_in_memory_database_without_mutating_target():
    src, target = _fixture(), _fixture()
    key = token_bytes(32)
    try:
        src.execute("INSERT INTO omega_fixture_records VALUES (?, ?)", (
            "synthetic-record-1", "synthetic-data-valid",
        ))
        backup = export_memory_fixture(src, key)
        target.execute("ATTACH DATABASE ':memory:' AS additional")
        with pytest.raises(SecurityDenied, match="RECOVERY_MEMORY_SQLITE_ONLY"):
            restore_memory_fixture(target, backup, key)
        assert target.execute("SELECT count(*) FROM omega_fixture_records").fetchone()[0] == 0
    finally:
        src.close()
        target.close()


def test_single_memory_database_still_works():
    src, target = _fixture(), _fixture()
    key = token_bytes(32)
    try:
        assert len(src.execute("PRAGMA database_list").fetchall()) == 1
        src.execute("INSERT INTO omega_fixture_records VALUES (?, ?)", (
            "synthetic-record-1", "synthetic-data-valid",
        ))
        assert restore_memory_fixture(target, export_memory_fixture(src, key), key) == 1
    finally:
        src.close()
        target.close()
