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


def test_index_only_secret_is_blocked_without_leaking(capsys):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git","init","-q"],cwd=d,check=True,capture_output=True)
        p=Path(d,"fixture.txt")
        marker="g"+"hp_"+("Z"*24)
        p.write_text("synthetic "+marker)
        subprocess.run(["git","add","fixture.txt"],cwd=d,check=True,capture_output=True)
        p.write_text("clean working tree, but index is sensitive")
        assert scan_quiet(cwd=d) is False
        assert marker not in capsys.readouterr().out

def test_binary_tracked_canary_is_blocked(capsys):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git","init","-q"],cwd=d,check=True,capture_output=True)
        marker="g"+"hp_"+("X"*24)
        Path(d,"fixture.bin").write_bytes(b"\\x00prefix"+marker.encode()+b"\\x00suffix")
        subprocess.run(["git","add","fixture.bin"],cwd=d,check=True,capture_output=True)
        assert scan_quiet(cwd=d) is False
        assert marker not in capsys.readouterr().out

def test_clean_index_and_worktree_pass():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git","init","-q"],cwd=d,check=True,capture_output=True)
        Path(d,"fixture.txt").write_text("clean synthetic fixture")
        subprocess.run(["git","add","fixture.txt"],cwd=d,check=True,capture_output=True)
        assert scan_quiet(cwd=d) is True

def test_git_runner_exception_fails_closed(capsys):
    def broken(*args,**kwargs):
        raise OSError("synthetic private path must never appear")
    assert scan_quiet(runner=broken) is False
    assert "synthetic private path" not in capsys.readouterr().out
