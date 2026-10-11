"""Exercise actual filename guard without logging any private fixture path."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/omega_privacy_filename_check.py"


def execute(filename=None, init=True):
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)
        if init:
            subprocess.run(["git", "init", "-q"], cwd=p, check=True,
                           capture_output=True)
        if filename:
            target = p / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("synthetic fixture", encoding="utf-8")
            subprocess.run(["git", "add", filename], cwd=p, check=True,
                           capture_output=True)
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=p,
                              capture_output=True, text=True)


def test_forbidden_filename_rejected_without_name_in_log():
    filename = ".env.fixture-private"
    result = execute(filename)
    assert result.returncode != 0
    assert filename not in result.stdout + result.stderr


def test_public_env_template_is_allowed():
    result = execute(".env.example")
    assert result.returncode == 0
    assert "OMEGA_PRIVATE_FILENAME_GUARD=PASS" in result.stdout


def test_unavailable_repository_is_rejected():
    result = execute(init=False)
    assert result.returncode != 0
    assert "fail-closed" in result.stdout
