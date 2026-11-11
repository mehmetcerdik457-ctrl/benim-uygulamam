"""Fail-closed structural preflight. This module NEVER grants production acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

class PreflightError(ValueError):
    pass

def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise PreflightError("duplicate JSON key: " + key)
        result[key] = value
    return result

def load_manifest(path):
    def reject_constant(value):
        raise PreflightError("invalid JSON constant: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=reject_constant)

def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def evaluate(record, evidence_root):
    findings = []
    if not isinstance(record, dict):
        raise PreflightError("record must be an object")
    expected = {"source_commit", "artifact_path", "artifact_sha256", "postgres_tests",
                "owner_approval", "auditor_approval", "deployment_receipt",
                "rollback_receipt", "billing_receipt"}
    extra = set(record) - expected
    if extra:
        findings.append("unknown fields: " + ",".join(sorted(extra)))
    commit = record.get("source_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        findings.append("invalid source commit")
    artifact = record.get("artifact_path")
    digest = record.get("artifact_sha256")
    if not isinstance(artifact, str) or not artifact or not isinstance(digest, str) or len(digest) != 64:
        findings.append("missing artifact metadata")
    else:
        root = Path(evidence_root).resolve()
        candidate = (root / artifact).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            findings.append("artifact unavailable or outside evidence root")
        elif _sha256(candidate) != digest.lower():
            findings.append("artifact SHA-256 mismatch")
    pg = record.get("postgres_tests")
    if not isinstance(pg, dict) or pg.get("historical_skips_executed") != 16 or pg.get("failed") != 0 or pg.get("skipped") != 0:
        findings.append("16 PostgreSQL tests not fully evidenced")
    for field in ("owner_approval", "auditor_approval", "deployment_receipt", "rollback_receipt", "billing_receipt"):
        if not isinstance(record.get(field), dict) or not record[field]:
            findings.append("missing " + field)
    # Presence of fields is NOT verification of signatures, identity, real tests or deployment.
    findings.append("independent cryptographic and deployment attestation not implemented")
    return {"schema": "omega.deployment.preflight.v1", "structural_findings": findings,
            "production_accepted": False, "production_admission": "DENIED_UNVERIFIED_ATTESTATION"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence-root", default=".")
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(load_manifest(args.manifest), args.evidence_root), sort_keys=True))
    except (PreflightError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"production_accepted": False, "error": str(exc)}))
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
