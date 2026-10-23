"""Real OMEGA public GitHub connector snapshot ingestion, no network."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
from omega_bridge.public_inventory import EXPECTED_URL, import_snapshot
ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/"docs/evidence/OMEGA_PUBLIC_GITHUB_SNAPSHOT_2026-10-20.json"

def record():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))

def test_real_public_repo_metadata_from_connected_github_is_ingestable():
    result=import_snapshot(record())
    assert result["inventory"]["repository"]=="mehmetcerdik457-ctrl/benim-uygulamam"
    assert result["inventory"]["visibility"]=="public"
    assert result["inventory"]["counts"]=={"stars":1,"forks":0,"watchers":1,"open_issues":83}
    assert result["provenance"]["source_url"]==EXPECTED_URL
    assert result["provenance"]["snapshot_only"] is True
    assert result["secrets_indexed"] is False
    assert result["owner_execution_authorized"] is False

def test_no_extra_field_can_be_silently_indexed():
    p=record()
    p["metadata"]["token"]="synthetic-not-real-secret"
    with pytest.raises(ValueError,match="PUBLIC_SNAPSHOT_DENIED"):
        import_snapshot(p)

@pytest.mark.parametrize("modification",[
    ("metadata","private",True),
    ("metadata","visibility","private"),
    ("metadata","full_name","out-of-scope/other"),
    ("provenance","source_url","https://example.invalid/"),
    ("provenance","verified_main_head","unverified"),
    ("provenance","live_refresh_enabled",True),
])
def test_untrusted_source_denied(modification):
    p=record()
    section,key,value=modification
    p[section][key]=value
    with pytest.raises(ValueError,match="PUBLIC_SNAPSHOT_DENIED"):
        import_snapshot(p)

def test_standalone_cli_returns_allowlisted_public_snapshot_only():
    run=subprocess.run([sys.executable,"-m","omega_bridge.public_inventory","--snapshot",str(SNAPSHOT)],
        cwd=ROOT,check=False,capture_output=True,text=True,timeout=10)
    assert run.returncode==0,run.stderr
    result=json.loads(run.stdout)
    assert result["inventory"]["repository"]=="mehmetcerdik457-ctrl/benim-uygulamam"
    assert "token" not in run.stdout.lower()
    assert "SYNTHETIC_CI" not in run.stdout
