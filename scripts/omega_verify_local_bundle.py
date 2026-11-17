"""Offline signed-receipt check: independently supplied keys and local evidence files.

A successful check authenticates the receipt and hashes; it NEVER admits production.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.omega_signed_deployment_receipt import ReceiptError, verify_receipt

class EvidenceBindingError(ValueError):
    pass

def local_digest(root, relative):
    if not isinstance(relative, str) or not relative or len(relative) > 240:
        raise EvidenceBindingError("invalid evidence path")
    if relative.startswith(("/", "./")) or "\\" in relative or ":" in relative:
        raise EvidenceBindingError("unsafe evidence path")
    parts = Path(relative).parts
    if any(p in (".", "..", "") for p in parts):
        raise EvidenceBindingError("path traversal")
    base = Path(root).resolve(strict=True)
    candidate = base
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise EvidenceBindingError("symlink evidence forbidden")
    if not candidate.is_file() or not candidate.resolve().is_relative_to(base):
        raise EvidenceBindingError("evidence file missing or outside root")
    if candidate.stat().st_size > 25 * 1024 * 1024:
        raise EvidenceBindingError("oversized evidence")
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def verify_local_bundle(receipt, root, paths, owner_key, auditor_key, *, commit, artifact_sha256, environment):
    if not isinstance(paths, dict) or set(paths) != {"artifact", "smoke", "rollback"}:
        raise EvidenceBindingError("exact artifact, smoke and rollback paths required")
    verdict = verify_receipt(receipt, owner_key, auditor_key, commit=commit,
                            artifact_sha256=artifact_sha256, environment=environment)
    for role, digest in (("artifact", artifact_sha256),
                         ("smoke", receipt["smoke_sha256"]),
                         ("rollback", receipt["rollback_sha256"])):
        if local_digest(root, paths[role]) != digest:
            raise EvidenceBindingError(role + " digest mismatch")
    return {**verdict, "local_evidence_hashes_verified": True,
            "production_accepted": False, "production_admission": "DENIED_UNVERIFIED_DEPLOYMENT"}

def main():
    parser = argparse.ArgumentParser()
    for name in ("receipt", "paths", "root", "owner-key", "auditor-key", "commit", "artifact-sha256", "environment"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        def read_json(path):
            if Path(path).is_symlink() or Path(path).stat().st_size > 65536:
                raise EvidenceBindingError("unsafe or oversized JSON")
            def pairs(items):
                result = {}
                for k, v in items:
                    if k in result:
                        raise EvidenceBindingError("duplicate JSON property")
                    result[k] = v
                return result
            return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                              parse_constant=lambda x: (_ for _ in ()).throw(EvidenceBindingError("nonfinite JSON")))
        verdict = verify_local_bundle(read_json(args.receipt), args.root, read_json(args.paths),
                    Path(args.owner_key).read_bytes(), Path(args.auditor_key).read_bytes(),
                    commit=args.commit, artifact_sha256=args.artifact_sha256, environment=args.environment)
        print(json.dumps(verdict, sort_keys=True))
    except (OSError, ValueError, TypeError, ReceiptError) as exc:
        print(json.dumps({"production_accepted": False, "error": str(exc)}))
    return 1  # No path through this offline check authorizes deployment.

if __name__ == "__main__":
    raise SystemExit(main())
