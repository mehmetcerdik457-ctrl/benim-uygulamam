#!/usr/bin/env python3
"""OMEGA-001..100 evidence gate; no network, subprocesses or implicit promotion.

Local SHA256 confirms log integrity, not that a test/deployment was honest.
For VERIFIED entries a separately configured Ed25519 authority must sign a
canonical evidence receipt; no trust key is shipped with this repository.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED = tuple(f"OMEGA-{n:03d}" for n in range(1, 101))
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


class EvidenceError(ValueError):
    pass


def _unique_object_pairs(pairs: list[tuple[str, object]]) -> dict:
    """Fail closed on ambiguous JSON keys at every nested object level."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON property")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise EvidenceError("nonfinite JSON value forbidden")


def _bounded_json_file(path: Path, max_bytes: int = 1024 * 1024) -> object:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise EvidenceError("missing, symlink, or oversized manifest")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object_pairs,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("invalid manifest JSON") from exc


def _local_file(root: Path, relpath: str) -> Path:
    if not isinstance(relpath, str) or not relpath or len(relpath) > 240:
        raise EvidenceError("invalid evidence path")
    if "\\" in relpath or ":" in relpath or relpath.startswith("/"):
        raise EvidenceError("non-portable or absolute evidence path")
    p = Path(relpath)
    if relpath.startswith("./") or "//" in relpath or any(part in (".", "..", "") for part in p.parts):
        raise EvidenceError("path traversal")
    candidate = root / p
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise EvidenceError("evidence symlink forbidden")
    if not candidate.is_file() or not candidate.resolve().is_relative_to(root.resolve()):
        raise EvidenceError("evidence file missing or outside root")
    return candidate


def _hash_file(path: Path, limit_bytes: int = 25 * 1024 * 1024) -> str:
    if path.stat().st_size > limit_bytes:
        raise EvidenceError("evidence log exceeds limit")
    h = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _verified(row: dict, root: Path, trusted_key_path: Path | None, owner_key_path: Path | None) -> str | None:
    proof = row.get("proof")
    if not isinstance(proof, dict):
        return "missing proof object"
    keys = {"source_commit", "test_log_path", "test_log_sha256", "run_id", "reviewer", "device", "owner_accepted", "signature", "owner_signature"}
    if keys - proof.keys():
        return "incomplete evidence receipt"
    if proof.keys() - keys:
        return "unexpected unsigned proof fields"
    if not isinstance(proof["source_commit"], str) or not COMMIT.fullmatch(proof["source_commit"]):
        return "invalid source commit SHA"
    if not isinstance(proof["test_log_sha256"], str) or not SHA256.fullmatch(proof["test_log_sha256"]):
        return "invalid log SHA256"
    if not isinstance(proof["run_id"], str) or not proof["run_id"].strip() or len(proof["run_id"]) > 160:
        return "missing exact test run ID"
    if not isinstance(proof["reviewer"], str) or not proof["reviewer"].strip() or len(proof["reviewer"]) > 120:
        return "missing independent reviewer"
    if not isinstance(proof["device"], str) or not proof["device"].strip() or len(proof["device"]) > 120:
        return "missing test device/platform"
    if proof["owner_accepted"] is not True:
        return "no owner acceptance"
    try:
        actual = _hash_file(_local_file(root, proof["test_log_path"]))
        if actual != proof["test_log_sha256"]:
            return "test log checksum mismatch"
    except (EvidenceError, OSError) as exc:
        return str(exc)
    if trusted_key_path is None or owner_key_path is None:
        return "independent auditor and owner public keys not configured"
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        payload = {k: proof[k] for k in sorted(keys - {"signature", "owner_signature"})}
        message = json.dumps({"requirement_id": row["id"], "proof": payload}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        raw_key = trusted_key_path.read_bytes()
        key = load_pem_public_key(raw_key)
        if not isinstance(key, Ed25519PublicKey):
            return "unsupported attestor key algorithm"
        owner_key = load_pem_public_key(owner_key_path.read_bytes())
        if not isinstance(owner_key, Ed25519PublicKey) or owner_key.public_bytes_raw() == key.public_bytes_raw():
            return "owner and auditor keys must be independent Ed25519 identities"
        signature = base64.b64decode(proof["signature"], validate=True)
        owner_signature = base64.b64decode(proof["owner_signature"], validate=True)
        key.verify(signature, message)
        owner_key.verify(owner_signature, message)
    except Exception:
        return "independent signature invalid or unavailable"
    return None


def evaluate(manifest: object, root: Path, trusted_key_path: Path | None = None, owner_key_path: Path | None = None) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != "omega.acceptance.v1":
        raise EvidenceError("invalid acceptance schema")
    rows = manifest.get("requirements")
    if not isinstance(rows, list) or len(rows) != 100:
        raise EvidenceError("must contain exactly 100 requirements")
    ids = [r.get("id") if isinstance(r, dict) else None for r in rows]
    if ids != list(EXPECTED):
        raise EvidenceError("requirements must be exactly OMEGA-001..100, ordered and unique")
    findings, accepted = [], 0
    for row in rows:
        if row.get("status") not in {"BLOCKED", "VERIFIED"}:
            raise EvidenceError(f"{row['id']}: invalid status")
        if row["status"] == "VERIFIED":
            reason = _verified(row, root, trusted_key_path, owner_key_path)
        else:
            reason = row.get("reason")
            if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
                raise EvidenceError(f"{row['id']}: missing bounded blocking reason")
        if reason is None:
            accepted += 1
            verdict = "VERIFIED"
        else:
            verdict = "BLOCKED"
        findings.append({"id": row["id"], "verdict": verdict, "reason": reason})
    return {"schema": "omega.acceptance.verdict.v1", "evaluated": 100,
            "verified": accepted, "blocked": 100 - accepted,
            "requirements_verified": accepted == 100,
            # No signed build/deploy/smoke/rollback receipt verifier exists in this
            # repository. Signed per-requirement test logs do not prove deployment.
            "production_accepted": False,
            "production_admission": "DENIED_NO_DEPLOYMENT_ATTESTATION",
            "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline 100-step acceptance proof gate")
    parser.add_argument("--manifest", type=Path, default=Path("evidence/omega-100-acceptance.json"))
    parser.add_argument("--evidence-root", type=Path, default=Path("."))
    parser.add_argument("--trusted-pubkey", type=Path, help="independent auditor Ed25519 PEM, not bundled")
    parser.add_argument("--owner-pubkey", type=Path, help="owner Ed25519 PEM, not bundled")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--enforce", action="store_true", help="production admission: deny until signed deployment/rollback attestation is implemented")
    modes.add_argument("--enforce-requirements", action="store_true", help="exit nonzero unless all 100 requirement proofs verify (never grants production)")
    args = parser.parse_args(argv)
    try:
        result = evaluate(_bounded_json_file(args.manifest), args.evidence_root, args.trusted_pubkey, args.owner_pubkey)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if args.enforce:
            return 0 if result["production_accepted"] else 1
        if args.enforce_requirements:
            return 0 if result["requirements_verified"] else 1
        return 0
    except EvidenceError as exc:
        print(json.dumps({"schema": "omega.acceptance.verdict.v1", "error": str(exc),
                          "production_accepted": False}, ensure_ascii=False), file=sys.stdout)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
