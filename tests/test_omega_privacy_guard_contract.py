"""Enforce real, self-contained, no-credential, deny-on-error privacy job."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_jobs_run_local_scans_with_readonly_scope():
    p = ROOT / ".github/workflows/privacy-guard.yml"
    data = yaml.load(p.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert data["permissions"] == {"contents": "read"}
    jobs = data["jobs"]
    assert list(jobs) == ["guard"]
    job = jobs["guard"]
    assert "uses" not in job
    assert job["timeout-minutes"] == "10"
    steps = job["steps"]
    assert steps[0]["with"]["persist-credentials"] == "false"
    commands = [x.get("run") for x in steps if x.get("run")]
    assert commands == ["python3 scripts/omega_privacy_filename_check.py",
                        "python3 scripts/omega_safe_secret_scan.py"]
    assert all("|| true" not in cmd and "set +e" not in cmd for cmd in commands)


def test_ci_is_local_no_reusable_external_workflow():
    p = ROOT / ".github/workflows/ci.yml"
    data = yaml.load(p.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert data["permissions"] == {"contents": "read"}
    job = data["jobs"]["baseline"]
    assert "uses" not in job and job["runs-on"] == "ubuntu-24.04"
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "python -m pytest -q" in commands
    assert "requirements-test.txt" in commands
    assert "|| true" not in commands
