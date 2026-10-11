"""Read-only contract tests for OMEGA matrix (no network and no secrets)."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "PROJECT_OMEGA_MASTER_SPEC_V2.md"
MATRIX = ROOT / "docs" / "OMEGA_REQUIREMENTS_MATRIX.csv"
FIELDS = [
    "Requirement ID", "Phase", "Priority", "Description", "Status",
    "Dependency", "Owner", "GitHub Issue", "Pull Request", "Commit SHA",
    "Test Evidence", "Acceptance Evidence", "Blocker", "Next Action",
]
STATUSES = {"DONE", "PARTIAL", "BLOCKED", "NOT_STARTED"}


def specification_requirements():
    phase = None
    out = {}
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^##\s+(FAZ\s+(?:0|I|II|III|IV|V|VI|VII|VIII|IX))\b", line)
        if match:
            phase = match.group(1)
        match = re.match(r"^(\d{1,3})\.\s+(.+)$", line)
        if match and phase:
            n = int(match.group(1))
            if 1 <= n <= 100:
                assert n not in out, f"duplicate requirement {n}"
                out[n] = (phase, match.group(2).strip())
    return out


def matrix_rows():
    with MATRIX.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS
        return list(reader)


def test_exactly_100_unique_requirement_ids_and_spec_text():
    original = specification_requirements()
    rows = matrix_rows()
    assert sorted(original) == list(range(1, 101))
    assert len(rows) == 100
    for n, row in enumerate(rows, start=1):
        assert row["Requirement ID"] == f"OMEGA-{n:03d}"
        assert (row["Phase"], row["Description"]) == original[n]


def test_statuses_are_bounded_and_done_requires_evidence():
    for row in matrix_rows():
        assert row["Status"] in STATUSES
        if row["Status"] == "DONE":
            assert row["Commit SHA"] and re.fullmatch(r"[0-9a-f]{40}", row["Commit SHA"])
            assert row["Test Evidence"] not in ("", "NOT_RUN_FOR_THIS_REQUIREMENT")
            assert row["Acceptance Evidence"] not in ("", "NOT_ACCEPTED")


def test_dependencies_earlier_and_no_private_inventory():
    for n, row in enumerate(matrix_rows(), start=1):
        if row["Dependency"]:
            assert re.fullmatch(r"OMEGA-\d{3}", row["Dependency"])
            assert 1 <= int(row["Dependency"][-3:]) < n
        assert "OPENAI_API_KEY=" not in str(row)
        assert "ghp_" not in str(row)
