"""OMEGA-094: bounded CycloneDX inventory of an isolated CI Python venv only.

No installed package metadata beyond *strictly validated name and version* is emitted.
No paths, download URLs, emails, credentials or raw METADATA are included.
This is not a container/OS SBOM, vulnerability scan, or production acceptance.
"""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

SHA = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+!\-]{0,127}\Z")
LIMIT = 512 * 1024


def _canonical(name):
    if type(name) is not str or not NAME.fullmatch(name):
        raise ValueError("unsafe_package_identity")
    return re.sub(r"[-_.]+", "-", name).lower()


def inventory(distributions, sha):
    if type(sha) is not str or not SHA.fullmatch(sha):
        raise ValueError("invalid_source_sha")
    seen = {}
    for dist in distributions:
        name = _canonical(dist.metadata["Name"])
        version = dist.version
        if type(version) is not str or not VERSION.fullmatch(version):
            raise ValueError("unsafe_package_version")
        if name in seen and seen[name] != version:
            raise ValueError("conflicting_package_versions")
        seen[name] = version
    if not 1 <= len(seen) <= 400:
        raise ValueError("package_count_outside_reviewed_scope")
    components = [
        {"type": "library", "name": name, "version": version,
         "bom-ref": f"pkg:pypi/{name}@{version}", "purl": f"pkg:pypi/{name}@{version}"}
        for name, version in sorted(seen.items())
    ]
    identity = sha + "\n" + "\n".join(f"{x['name']}=={x['version']}" for x in components)
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, identity)),
        "metadata": {
            "component": {"type": "application", "name": "omega-disposable-python-ci",
                          "version": sha[:12]},
            "properties": [
                {"name": "omega:source-commit-sha", "value": sha},
                {"name": "omega:scope", "value": "isolated-ci-python-venv-only"},
                {"name": "omega:full-oci-os-sbom", "value": "NOTRUN"},
                {"name": "omega:image-cve-scan", "value": "NOTRUN"},
            ]
        },
        "components": components,
    }


def run(output, expected_sha):
    current = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True).stdout.strip()
    if current != expected_sha:
        raise ValueError("checkout_sha_mismatch")
    # This script must run from an explicitly allocated ephemeral test venv.
    if sys.prefix == sys.base_prefix or os.environ.get("OMEGA_SBOM_CI_SCOPE") != "disposable-venv":
        raise ValueError("isolated_ci_venv_required")
    output = Path(output)
    tempdir = Path(os.environ["RUNNER_TEMP"]).resolve()
    if output.parent.resolve() != tempdir or output.suffix != ".json":
        raise ValueError("unsafe_output_destination")
    data = inventory(md.distributions(), current)
    encoded = (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    if len(encoded) > LIMIT:
        raise ValueError("sbom_output_too_large")
    output.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    print("OMEGA_PYTHON_VENV_SBOM=PASS")
    print("OMEGA_PYTHON_VENV_SBOM_SHA256=" + digest)
    print("OMEGA_PYTHON_VENV_SBOM_COMPONENTS=" + str(len(data["components"])))
    print("OMEGA_PYTHON_VENV_SBOM_CHECKOUT_SHA=" + current)
    print("OMEGA_OCI_OS_SBOM=NOTRUN")
    print("OMEGA_IMAGE_CVE_SCAN=NOTRUN")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--sha", required=True)
    args = p.parse_args()
    try:
        run(args.output, args.sha)
    except (ValueError, OSError, subprocess.SubprocessError, KeyError):
        print("OMEGA_PYTHON_VENV_SBOM=FAIL_CLOSED", file=sys.stderr)
        raise SystemExit(2)
