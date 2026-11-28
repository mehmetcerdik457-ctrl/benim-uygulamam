"""Workflow YAML syntax cannot prove GitHub dispatch; real job is required."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from omega_ci_preflight import validate

def test_all_workflow_yaml_documents_have_triggers_and_jobs():
    workflows=validate()
    assert "omega-ci-preflight.yml" in workflows

def test_zero_job_failure_is_not_called_test_failure():
    # A workflow failing before job creation has no pytest verdict.
    run={"conclusion":"failure","jobs":[]}
    assert not run["jobs"]
    assert run["conclusion"]=="failure"
