"""Regression contract: credential matches must never be echoed into CI logs."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".github/workflows/privacy-guard.yml"


def test_privacy_guard_uses_quiet_match():
    content = GUARD.read_text(encoding="utf-8")
    assert 'git grep -I -q -E "$markers"' in content
    assert not re.search(r"git grep[^\n]*\s-n\b[^\n]*\$markers", content)


def test_privacy_guard_does_not_print_matching_lines():
    content = GUARD.read_text(encoding="utf-8")
    assert 'git grep -I -n -E "$markers"' not in content
    assert 'Potential credential material detected.' in content
