"""Real isolated Git command canaries: binary scan and fail-closed exit status."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from omega_safe_secret_scan import scan_quiet

def test_tracked_binary_canary_must_block_without_echo(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git","init","-q"],cwd=tmp,check=True,capture_output=True)
        secret=b"g"+b"hp_"+b"S"*25  # generated fake canary, never a real credential
        Path(tmp,"synthetic.bin").write_bytes(b"offline fixture\x00"+secret+b"\x00")
        subprocess.run(["git","add","synthetic.bin"],cwd=tmp,check=True,capture_output=True)
        assert scan_quiet(cwd=tmp) is False
        captured=capsys.readouterr()
        assert not captured.out and not captured.err
        assert secret.decode() not in repr(captured)

def test_return_codes_distinguish_absent_match_from_scan_failure(capsys):
    for status,expected in [(0,False),(1,True),(2,False),(128,False)]:
        def fake_runner(args,**kw):
            assert args[:4]==["git","grep","-a","-q"]
            assert kw["stdout"]==subprocess.DEVNULL
            assert kw["stderr"]==subprocess.DEVNULL
            assert kw["check"] is False
            return SimpleNamespace(returncode=status)
        assert scan_quiet(runner=fake_runner) is expected
    result=capsys.readouterr()
    assert not result.out and not result.err

def test_valid_git_repo_without_secrets_passes_even_with_binary_fixture():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git","init","-q"],cwd=tmp,check=True,capture_output=True)
        Path(tmp,"safe.bin").write_bytes(b"example\x00public metadata\x00")
        subprocess.run(["git","add","safe.bin"],cwd=tmp,check=True,capture_output=True)
        assert scan_quiet(cwd=tmp) is True
