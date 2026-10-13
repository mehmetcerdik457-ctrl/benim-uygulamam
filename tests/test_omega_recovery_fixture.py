"""OMEGA-029: disposable in-memory SQLite, no owner backups, secrets or accounts."""

from dataclasses import replace
from secrets import token_bytes
import sqlite3

import pytest

from omega_mvi.security.offline_contract import SecurityDenied
from omega_mvi.security.recovery_fixture import (
    SyntheticBackup, create_memory_fixture, export_memory_fixture,
    restore_memory_fixture,
)


def new_db():
    conn = sqlite3.connect(":memory:")
    create_memory_fixture(conn)
    return conn


def test_029_real_sqlite_fixture_encrypt_backup_restore_roundtrip(tmp_path):
    source, target = new_db(), new_db()
    key = token_bytes(32)
    try:
        source.executemany("INSERT INTO omega_fixture_records(id,value) VALUES(?,?)", [
            ("synthetic-record-1", "synthetic-data-alpha"),
            ("synthetic-record-2", "synthetic-data-beta")
        ])
        backup = export_memory_fixture(source, key)
        assert backup.version == 1
        assert len(backup.sha256_hex) == 64
        assert b"synthetic-data-alpha" not in backup.envelope
        # A disposable file is ONLY used as an encrypted artifact transport.
        disposable_file = tmp_path / "synthetic-only-encrypted-snapshot.bin"
        disposable_file.write_bytes(backup.envelope)
        from_disk = replace(backup, envelope=disposable_file.read_bytes())
        assert restore_memory_fixture(target, from_disk, key) == 2
        assert source.execute("SELECT id,value FROM omega_fixture_records ORDER BY id").fetchall() == (
            target.execute("SELECT id,value FROM omega_fixture_records ORDER BY id").fetchall()
        )
    finally:
        source.close()
        target.close()


def test_029_wrong_key_tamper_manifest_and_version_refused():
    source, target = new_db(), new_db()
    key = token_bytes(32)
    try:
        source.execute("INSERT INTO omega_fixture_records VALUES (?,?)",
                       ("synthetic-record-1", "synthetic-data-safe"))
        backup = export_memory_fixture(source, key)
        with pytest.raises(SecurityDenied, match="BACKUP_INTEGRITY_DENIED"):
            restore_memory_fixture(target, backup, token_bytes(32))
        with pytest.raises(SecurityDenied, match="RECOVERY_MANIFEST_DENIED"):
            restore_memory_fixture(target, replace(backup, version=2), key)
        with pytest.raises(SecurityDenied, match="RECOVERY_MANIFEST_DENIED"):
            restore_memory_fixture(target, replace(backup, sha256_hex="0" * 64), key)
        damaged = bytearray(backup.envelope)
        damaged[-1] ^= 1
        with pytest.raises(SecurityDenied, match="RECOVERY_MANIFEST_DENIED"):
            restore_memory_fixture(target, replace(backup, envelope=bytes(damaged)), key)
        assert target.execute("SELECT COUNT(*) FROM omega_fixture_records").fetchone()[0] == 0
    finally:
        source.close()
        target.close()


def test_029_disk_sqlite_never_accepted_for_source_or_restore(tmp_path):
    file_db = sqlite3.connect(tmp_path / "not-allowed.sqlite")
    memory = new_db()
    key = token_bytes(32)
    try:
        with pytest.raises(SecurityDenied, match="RECOVERY_MEMORY_SQLITE_ONLY"):
            create_memory_fixture(file_db)
        with pytest.raises(SecurityDenied, match="RECOVERY_MEMORY_SQLITE_ONLY"):
            export_memory_fixture(file_db, key)
        snapshot = export_memory_fixture(memory, key)
        with pytest.raises(SecurityDenied, match="RECOVERY_MEMORY_SQLITE_ONLY"):
            restore_memory_fixture(file_db, snapshot, key)
    finally:
        file_db.close()
        memory.close()


def test_029_real_like_values_and_over_limit_rejected_without_snapshot():
    source = new_db()
    try:
        source.execute("INSERT INTO omega_fixture_records VALUES (?,?)",
                       ("production-record-1", "synthetic-data-x"))
        with pytest.raises(SecurityDenied, match="RECOVERY_NON_SYNTHETIC_PAYLOAD"):
            export_memory_fixture(source, token_bytes(32))
        source.execute("DELETE FROM omega_fixture_records")
        source.execute("INSERT INTO omega_fixture_records VALUES (?,?)",
                       ("synthetic-record-1", "nonfixture-production-like-value"))
        with pytest.raises(SecurityDenied, match="RECOVERY_NON_SYNTHETIC_PAYLOAD"):
            export_memory_fixture(source, token_bytes(32))
        source.execute("DELETE FROM omega_fixture_records")
        for index in range(17):
            source.execute("INSERT INTO omega_fixture_records VALUES (?,?)",
                           (f"synthetic-record-{index}", f"synthetic-data-{index}"))
        with pytest.raises(SecurityDenied, match="RECOVERY_NON_SYNTHETIC_PAYLOAD"):
            export_memory_fixture(source, token_bytes(32))
    finally:
        source.close()


def test_029_nonempty_restore_target_never_overwritten():
    source, target = new_db(), new_db()
    key = token_bytes(32)
    try:
        source.execute("INSERT INTO omega_fixture_records VALUES (?,?)",
                       ("synthetic-record-source", "synthetic-data-src"))
        target.execute("INSERT INTO omega_fixture_records VALUES (?,?)",
                       ("synthetic-record-existing", "synthetic-data-original"))
        snapshot = export_memory_fixture(source, key)
        with pytest.raises(SecurityDenied, match="RECOVERY_TARGET_NOT_EMPTY"):
            restore_memory_fixture(target, snapshot, key)
        assert target.execute("SELECT * FROM omega_fixture_records").fetchall() == [
            ("synthetic-record-existing", "synthetic-data-original")
        ]
    finally:
        source.close()
        target.close()


def test_029_missing_sentinel_and_unexpected_existing_schema_fail_closed():
    conn = sqlite3.connect(":memory:")
    try:
        with pytest.raises(SecurityDenied, match="RECOVERY_SENTINEL_MISSING"):
            export_memory_fixture(conn, token_bytes(32))
        conn.execute("CREATE TABLE other_tenant(id TEXT)")
        with pytest.raises(SecurityDenied, match="RECOVERY_NONEMPTY_DATABASE"):
            create_memory_fixture(conn)
    finally:
        conn.close()
