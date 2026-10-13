"""Offline direct Python dependency SBOM; NEVER claims a full transitive SBOM.

Only the three reviewed repository requirement manifests are accessible.
No network, shell, package installation, host inventory or private paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = frozenset({
    "requirements.txt",
    "omega_mvi/requirements.txt",
    "omega_mvi/requirements-test.txt",
})
PIN = re.compile(
    r"([A-Za-z][A-Za-z0-9_.-]{0,127})"
    r"(?:\\[([A-Za-z0-9_,.-]{1,128})\\])?"
    r"==([0-9][A-Za-z0-9.!+_-]{0,79})\\Z"
)


class ManifestDenied(Exception):
    """Fixed error code; never incorporate untrusted manifest content."""


def direct_pins(root: Path = ROOT) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    seen: set[str] = set()

    def load(rel: str) -> None:
        if rel not in ALLOWED:
            raise ManifestDenied("UNREVIEWED_REQUIREMENTS_FILE")
        if rel in seen:
            return
        seen.add(rel)
        path = root / rel
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
                raise ManifestDenied("UNSAFE_REQUIREMENTS_FILE")
            data = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError, ValueError) as exc:
            raise ManifestDenied("UNREADABLE_REQUIREMENTS_FILE") from None
        for raw in data.splitlines():
            if len(raw) > 256:
                raise ManifestDenied("INVALID_REQUIREMENTS_LINE")
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Only space-then-hash comments are accepted, not arbitrary
            # expressions, environment markers, URLs, or install switches.
            line = line.split(" #", 1)[0].strip()
            if line == "-r requirements.txt" and rel == "omega_mvi/requirements-test.txt":
                load("omega_mvi/requirements.txt")
                continue
            match = PIN.fullmatch(line)
            if match is None:
                raise ManifestDenied("UNPINNED_OR_UNREVIEWED_DEPENDENCY")
            name, extras, version = match.groups()
            normalized = re.sub(r"[-_.]+", "-", name).lower()
            key = normalized
            extra = ",".join(sorted(extras.lower().split(","))) if extras else ""
            item = {"name": normalized, "version": version, "extras": extra}
            previous = found.get(key)
            if previous is not None and previous != item:
                raise ManifestDenied("CONFLICTING_DEPENDENCY_PINS")
            found[key] = item

    for rel in sorted(ALLOWED):
        load(rel)
    return [found[name] for name in sorted(found)]


def document(root: Path = ROOT) -> dict:
    components = []
    for item in direct_pins(root):
        name, version, extras = item["name"], item["version"], item["extras"]
        component = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": "pkg:pypi/" + name + "@" + version,
            "bom-ref": "pkg:pypi/" + name + "@" + version,
            "scope": "required",
        }
        if extras:
            component["properties"] = [{"name": "omega:declared-extra", "value": extras}]
        components.append(component)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "omega-public-demo-direct-python"},
            "properties": [
                {"name": "omega:inventory-scope", "value": "DIRECT_PYTHON_PINS_ONLY"},
                {"name": "omega:transitive-dependencies", "value": "NOTRUN"},
                {"name": "omega:image-digests", "value": "NOTRUN"},
                {"name": "omega:vulnerability-scan", "value": "NOTRUN"},
                {"name": "omega:production-accepted", "value": "false"},
            ],
        },
        "components": components,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Write direct-only CycloneDX JSON to stdout")
    args = parser.parse_args(argv)
    try:
        output = json.dumps(document(), sort_keys=True, separators=(",", ":"))
    except ManifestDenied as exc:
        print("OMEGA_DIRECT_SBOM=" + str(exc))
        return 2
    if args.json:
        print(output)
    else:
        print("OMEGA_DIRECT_SBOM=DIRECT_PINS_ONLY_NOT_PRODUCTION_SBOM")
        print("OMEGA_DIRECT_SBOM_SHA256=" + hashlib.sha256(output.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
