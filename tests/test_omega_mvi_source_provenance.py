"""Check PR58 frozen source-byte provenance and adversarial manifest handling."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import omega_verify_reused_mvi as v
from scripts.omega_verify_legacy_bytes import EvidenceError
M = ROOT/"docs/evidence/OMEGA_058_SOURCE_GIT_BLOBS.json"

def item(name,data):
    sha=hashlib.sha1(f"blob {len(data)}".encode()+bytes([0])+data).hexdigest()
    return {"path":name,"size":len(data),"git_blob_sha1":sha}

def manifest(*entries):
    return {"schema":v.SCHEMA,"source_commit":v.SOURCE,"items":list(entries)}

def test_77_real_source_blobs_still_match_exact_original_bytes():
    m=json.loads(M.read_text(encoding="utf-8"))
    assert len(m["items"])==77
    result=v.verify(ROOT,m)
    assert result["matched"]==77 and result["checked"]==77
    assert result["source_bytes_identical"] is True
    assert result["original_100_requirement_acceptance"]=="NOT_DETERMINED"

def test_tampered_blob_cannot_pass(tmp_path):
    (tmp_path/"file.txt").write_bytes(b"changed")
    assert v.verify(tmp_path,manifest(item("file.txt",b"original")))["changed"]==1

def test_broken_manifest_fails_before_read(tmp_path,monkeypatch):
    m=manifest(item("anything",b"x"),item("anything",b"x"))
    monkeypatch.setattr(v,"_open_regular_no_links",lambda *_: pytest.fail("read before validation"))
    with pytest.raises(EvidenceError,match="DUPLICATE_PATH"):
        v.verify(tmp_path,m)

@pytest.mark.parametrize("bad",["../escape","/absolute","a//b","a/./b","a/../b"])
def test_path_traversal_rejected(tmp_path,bad):
    with pytest.raises(EvidenceError,match="INVALID_PATH"):
        v.verify(tmp_path,manifest(item(bad,b"x")))

def test_symlinked_parent_counted_unsafe(tmp_path):
    (tmp_path/"real").mkdir()
    (tmp_path/"real"/"f").write_bytes(b"x")
    (tmp_path/"link").symlink_to(tmp_path/"real",target_is_directory=True)
    result=v.verify(tmp_path,manifest(item("link/f",b"x")))
    assert result["unsafe"]==1 and not result["source_bytes_identical"]
