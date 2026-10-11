"""Read-only workflow parse preflight; cannot diagnose GitHub server admission."""
from pathlib import Path
import yaml

WORKFLOWS=Path(__file__).resolve().parents[1]/".github"/"workflows"

def validate():
    paths=sorted((*WORKFLOWS.glob("*.yml"),*WORKFLOWS.glob("*.yaml")))
    if not paths:
        raise AssertionError("No workflows")
    for path in paths:
        data=yaml.load(path.read_text(encoding="utf-8"),Loader=yaml.BaseLoader)
        if not isinstance(data,dict) or not isinstance(data.get("jobs"),dict) or not isinstance(data.get("on"),dict):
            raise AssertionError(f"Malformed workflow structure: {path.name}")
        if not data["jobs"]:
            raise AssertionError(f"No jobs declared: {path.name}")
    return [p.name for p in paths]

if __name__=="__main__":
    print("OMEGA_WORKFLOW_YAML_PRECHECK=PASS",len(validate()))
