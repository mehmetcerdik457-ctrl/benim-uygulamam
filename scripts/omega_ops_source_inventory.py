"""OMEGA-094 conservative inventory: evidence, NEVER a full SBOM or CVE scan."""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.+!-]+$")
SHA_ACTION = re.compile(r"@[0-9a-f]{40}(?:\s|$)")


def requirement_pins(path, seen=None):
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return []
    seen.add(path)
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            entries.extend(requirement_pins(path.parent / line[3:].strip(), seen))
        else:
            entries.append({"pinned": bool(PIN.fullmatch(line))})
    return entries


def inventory(root=ROOT):
    requirements = []
    for filename in ("omega_mvi/requirements.txt",
                     "omega_mvi/requirements-test.txt", "requirements.txt"):
        requirements.extend(requirement_pins(root / filename))
    bases = []
    for name in ("omega_mvi/Dockerfile", "omega_mvi/Dockerfile.test"):
        for line in (root / name).read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.upper().startswith("FROM "):
                bases.append(s.split()[1])
    compose = (root / "compose.omega.yml").read_text(encoding="utf-8")
    bases.extend(re.findall(r"^\s+image:\s*(\S+)", compose, re.MULTILINE))
    actions = []
    for path in (root / ".github/workflows").glob("*.yml"):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.search(r"^\s*-?\s*uses:\s*([^#]+)", line)
            if m:
                action = m.group(1).strip()
                if not action.startswith("./"):
                    actions.append(bool(SHA_ACTION.search(action)))
    return {
        "scope": "repository-static-source-inventory-only",
        "checked_out_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip(),
        "direct_requirements": len(requirements),
        "direct_requirements_pinned": sum(x["pinned"] for x in requirements),
        "container_image_references": len(bases),
        "container_images_digest_pinned": sum("@sha256:" in b for b in bases),
        "github_actions_references": len(actions),
        "github_actions_sha_pinned": sum(actions),
        "complete_transitive_sbom": "NOTRUN",
        "image_vulnerability_scan": "NOTRUN",
        "runtime_grafana_observation": "NOTRUN",
        "production_supply_chain_acceptance": "NOT_ACCEPTED",
    }


if __name__ == "__main__":
    print(json.dumps(inventory(), sort_keys=True, ensure_ascii=True))
