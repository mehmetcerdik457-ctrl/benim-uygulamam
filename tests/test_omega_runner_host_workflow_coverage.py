"""Prevent loss of exact-HEAD runner-host release gates on MVI changes.

These contract tests exercise only a checked-in GitHub Actions workflow.
They cannot validate a live Docker daemon, the owner's device or production.
"""
from fnmatch import fnmatchcase
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "omega-runner-host-acceptance.yml"
HEAD_REF = "${{ github.event.pull_request.head.sha || github.sha }}"


def _workflow():
    # BaseLoader retains YAML 'on' as a string rather than YAML 1.1 boolean.
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_sensitive_implementation_changes_trigger_runner_host_gate():
    workflow = _workflow()
    triggers = workflow["on"]["pull_request"]["paths"]
    for source_path in (
        "compose.omega.yml",
        "omega_mvi/inspection/github_inventory/__init__.py",
        "omega_mvi/inspection/pipeline.py",
        "omega_mvi/app/main.py",
        "omega_mvi/ingress/nginx.conf",
        "scripts/omega_network_topology_gate.py",
        "scripts/omega_ingress_config_gate.py",
        "scripts/omega_runner_host_diagnostic.py",
        "scripts/omega_runner_host_port_audit.py",
        "tests/test_omega_runner_host_workflow_coverage.py",
    ):
        assert any(fnmatchcase(source_path, pattern) for pattern in triggers), (
            "Host gate must rerun for changed source: " + source_path
        )


def test_runner_acceptance_pins_and_verifies_actual_pr_head():
    workflow = _workflow()
    steps = workflow["jobs"]["runner-host-acceptance"]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] == "false"
    assert checkout["with"]["ref"] == HEAD_REF

    verify = next(step for step in steps if step.get("name", "").startswith("Enforce exact PR source"))
    assert verify["env"]["OMEGA_EXPECTED_SHA"] == HEAD_REF
    assert 'git rev-parse HEAD' in verify["run"]
    assert '"$OMEGA_EXPECTED_SHA"' in verify["run"]


def test_required_host_and_port_enforcement_cannot_be_skipped():
    workflow = _workflow()
    job = workflow["jobs"]["runner-host-acceptance"]
    assert workflow["permissions"] == {"contents": "read"}
    steps = job["steps"]
    port = next(step for step in steps if step.get("name") == "Enforce requested versus EFFECTIVE Docker host port mapping")
    host = next(step for step in steps if step.get("name") == "Enforce independent runner-host connectivity acceptance")
    assert port["run"].strip() == "python3 scripts/omega_runner_host_port_audit.py"
    assert host["run"].strip() == "python3 scripts/omega_runner_host_diagnostic.py --require-runner-host"
    for step in (port, host):
        assert step.get("if") == "success() || failure()"
        assert "continue-on-error" not in step
    assert not job.get("continue-on-error")
