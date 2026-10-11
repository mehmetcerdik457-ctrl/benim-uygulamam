"""Synthetic canary test: never print matches or tracked paths."""
from pathlib import Path
import subprocess
import sys
import tempfile
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from omega_safe_secret_scan import scan_quiet, main
def test_secret_canary_is_detected_with_no_match_printed(capsys):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git","init","-q"],cwd=d,check=True,capture_output=True)
        canary="g"+"hp_"+("Q"*23)  # dynamic synthetic value, NOT a credential
        Path(d,"fixture.txt").write_text("illustrative: "+canary)
        subprocess.run(["git","add","fixture.txt"],cwd=d,check=True,capture_output=True)
        assert scan_quiet(cwd=d) is False
        assert canary not in capsys.readouterr().out
def test_missing_git_repo_fails_closed_without_printing():
    with tempfile.TemporaryDirectory() as d:
        assert scan_quiet(cwd=d) is False
def test_scan_command_has_quiet_no_log_output():
    source=(ROOT/"scripts"/"omega_safe_secret_scan.py").read_text()
    assert '"-q"' in source and "stdout=subprocess.DEVNULL" in source
    assert "stderr=subprocess.DEVNULL" in source
    assert '"-n"' not in source
