"""Independent offline checks for restored 0.1.5/0.1.4 archive receipts.

No real credentials, local owner files, network or production state are used.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.omega_verify_legacy_bytes import EvidenceError, main, verify


def entry(path: str, data: bytes):
    return {"relative_path": path, "sha256": hashlib.sha256(data).hexdigest()}


def manifest(*items):
    return {"schema": "omega-recovered-bytes-v1", "source_version": "test-only", "items": list(items)}


def test_real_local_bytes_match_and_are_not_changed(tmp_path):
    (tmp_path / "artifacts").mkdir()
    a, b = b"offline-source-archive-test", b'{"manifest":"synthetic"}'
    (tmp_path / "artifacts/a.tar.gz").write_bytes(a)
    (tmp_path / "artifacts/b.json").write_bytes(b)
    m = manifest(entry("artifacts/a.tar.gz", a), entry("artifacts/b.json", b))
    result = verify(tmp_path, m)
    assert result["files_checked"] == 2
    assert result["files_matched"] == 2
    assert result["byte_integrity_passed"] is True
    assert result["original_requirement_acceptance"] == "NOT_DETERMINED"
    assert (tmp_path / "artifacts/a.tar.gz").read_bytes() == a


def test_changed_archive_does_not_pass(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"changed")
    result = verify(tmp_path, manifest(entry("a.bin", b"original")))
    assert result["files_mismatched"] == 1
    assert result["byte_integrity_passed"] is False


def test_missing_archive_stays_unverified(tmp_path):
    result = verify(tmp_path, manifest(entry("missing.tar.gz", b"archive")))
    assert result["files_missing"] == 1
    assert result["byte_integrity_passed"] is False


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "a/./b", "a//b", "a/../b", "a\\b"])
def test_unsafe_manifest_paths_rejected_before_file_access(tmp_path, unsafe):
    with pytest.raises(EvidenceError, match="INVALID_PATH"):
        verify(tmp_path, manifest(entry(unsafe, b"x")))


def test_duplicate_paths_and_wrong_hash_format_rejected(tmp_path):
    with pytest.raises(EvidenceError, match="DUPLICATE_PATH"):
        verify(tmp_path, manifest(entry("a.bin", b"a"), entry("a.bin", b"a")))
    with pytest.raises(EvidenceError, match="INVALID_SHA256"):
        verify(tmp_path, manifest({"relative_path": "a.bin", "sha256": "bad"}))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks not available")
def test_symlinked_artifacts_must_not_be_followed(tmp_path):
    (tmp_path / "real.bin").write_bytes(b"secret-not-to-read")
    (tmp_path / "linked.bin").symlink_to(tmp_path / "real.bin")
    result = verify(tmp_path, manifest(entry("linked.bin", b"secret-not-to-read")))
    assert result["byte_integrity_passed"] is False


def test_cli_outputs_only_count_evidence_and_nonzero_on_mismatch(tmp_path, capsys):
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"test-bytes")
    m = manifest(entry("archive.zip", b"test-bytes"))
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(m), encoding="utf-8")
    assert main(["--root", str(tmp_path), "--manifest", str(path)]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["byte_integrity_passed"] is True
    assert "test-bytes" not in str(response)
    archive.write_bytes(b"changed")
    assert main(["--root", str(tmp_path), "--manifest", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["byte_integrity_passed"] is False


def test_archived_015_receipt_is_claim_only_until_original_bytes_present(tmp_path):
    file = ROOT / "docs/evidence/OMEGA_015_HISTORICAL_SOURCE_HASHES.json"
    m = json.loads(file.read_text(encoding="utf-8"))
    assert m["schema"] == "omega-recovered-bytes-v1"
    assert m["source_version"] == "0.1.5-dev"
    assert len(m["items"]) == 2
    result = verify(tmp_path, m)
    assert result["files_missing"] == 2
    assert result["byte_integrity_passed"] is False
