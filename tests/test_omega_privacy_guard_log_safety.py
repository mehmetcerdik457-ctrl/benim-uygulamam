"""Synthetic-only tests for the actual git grep command used by Privacy Guard."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".github/workflows/privacy-guard.yml"
MARKER = "ghp_" + "A" * 20


def scan(directory):
    return subprocess.run(
        ["git", "grep", "-I", "-q", "-E", r"ghp_[A-Za-z0-9]{20,}", "--", "."],
        cwd=directory, capture_output=True, text=True,
    )


def make_repo(content):
    directory = tempfile.TemporaryDirectory()
    p = Path(directory.name)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True)
    (p / "sample.txt").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=p, check=True)
    return directory


def test_detected_synthetic_marker_is_quiet():
    with make_repo(MARKER) as p:
        result = scan(p)
        assert result.returncode == 0
        assert MARKER not in result.stdout + result.stderr
        assert result.stdout == ""


def test_no_match_is_one():
    with make_repo("ordinary safe text") as p:
        assert scan(p).returncode == 1


def test_scan_error_is_not_no_match():
    with tempfile.TemporaryDirectory() as p:
        assert scan(p).returncode not in (0, 1)


def test_guard_fails_closed_and_does_not_echo_match():
    content = GUARD.read_text(encoding="utf-8")
    assert 'git grep -I -q -E "$markers"' in content
    assert 'scan_status=$?' in content
    assert '*) echo "Privacy scan failed; fail-closed."; exit 1 ;;' in content
    assert '0) echo "Potential credential material detected."; exit 1 ;;' in content
    assert '1) echo "PRIVACY_GUARD=PASS" ;;' in content
    assert 'git grep -I -n -E "$markers"' not in content
