"""Real git fixture tests; private-state path strings are never emitted by the guard."""
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/omega_privacy_filename_check.py"
sys.path.insert(0, str(ROOT / "scripts"))
from omega_privacy_filename_check import scan


def run_fixture(name=None, init=True):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        if init:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
        if name:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
            subprocess.run(["git", "add", name], cwd=root, check=True, capture_output=True)
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=root,
                              capture_output=True, text=True)


def test_private_name_denied_and_not_echoed():
    name = "nested/.env.test-private"
    response = run_fixture(name)
    assert response.returncode != 0
    assert name not in (response.stdout + response.stderr)


def test_binary_extension_denied_without_filename_disclosure():
    name = "nested/fixture.key.properties".replace("fixture.key.properties", "key.properties")
    response = run_fixture(name)
    assert response.returncode != 0
    assert name not in response.stdout + response.stderr


def test_allowlisted_example():
    response = run_fixture(".env.example")
    assert response.returncode == 0
    assert "OMEGA_PRIVATE_FILENAME_GUARD=PASS" in response.stdout


def test_no_repository_fails_closed():
    response = run_fixture(init=False)
    assert response.returncode != 0
    assert "fail-closed" in response.stdout


def test_git_binary_missing_fails_closed_without_subprocess_output():
    def missing(*args, **kwargs):
        raise FileNotFoundError("would-be-sensitive-local-path")
    from unittest.mock import patch
    with patch("omega_privacy_filename_check.subprocess.run", side_effect=missing):
        assert scan() == 2
