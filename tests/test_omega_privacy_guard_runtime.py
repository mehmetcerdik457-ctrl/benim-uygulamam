"""Execute the REAL workflow scan shell block in disposable git fixtures."""
from pathlib import Path
import subprocess
import tempfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privacy-guard.yml"
SYNTHETIC = "ghp_" + "A" * 24


def scan_block():
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return next(step["run"] for step in workflow["jobs"]["guard"]["steps"]
                if step.get("name") == "Scan text files for credential markers")


def run_case(content, initialized=True):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        if initialized:
            subprocess.run(["git", "init", "-q"], cwd=path, check=True,
                           capture_output=True)
            (path / "fixture.txt").write_text(content, encoding="utf-8")
            subprocess.run(["git", "add", "fixture.txt"], cwd=path,
                           check=True, capture_output=True)
        result = subprocess.run(
            ["bash", "-c", scan_block()], cwd=path,
            capture_output=True, text=True, check=False,
        )
        return result


@pytest.mark.parametrize("content,expected", [
    (SYNTHETIC, 1),
    ("ordinary nonsecret text", 0),
], ids=["synthetic-match", "no-match"])
def test_actual_workflow_shell_distinguishes_match_from_no_match(content, expected):
    result = run_case(content)
    assert result.returncode == expected
    assert SYNTHETIC not in (result.stdout + result.stderr)


def test_actual_workflow_shell_fails_closed_on_git_error():
    result = run_case("safe", initialized=False)
    assert result.returncode != 0
    assert "Privacy scan failed; fail-closed." in result.stdout


def test_actual_workflow_does_not_echo_secret_or_matching_line():
    value = "surrounding private material " + SYNTHETIC + " end"
    result = run_case(value)
    assert result.returncode == 1
    assert SYNTHETIC not in result.stdout + result.stderr
    assert "surrounding private material" not in result.stdout + result.stderr
