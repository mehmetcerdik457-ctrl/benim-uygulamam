"""Check exact Git blob bytes of the frozen public PR58 import without network."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from scripts.omega_verify_legacy_bytes import EvidenceError, _open_regular_no_links, _relative

SCHEMA = "omega-mvi-git-blob-source-v1"
SOURCE = "044c558b2b28e05929a9acd79a639a32092ab187"
MAX_BYTES = 1024 * 1024


def verify(root: Path, manifest: dict) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA or manifest.get("source_commit") != SOURCE:
        raise EvidenceError("INVALID_MANIFEST")
    records = manifest.get("items")
    if not isinstance(records, list) or not 1 <= len(records) <= 300:
        raise EvidenceError("INVALID_MANIFEST")
    if not root.is_dir() or root.is_symlink():
        raise EvidenceError("ROOT_UNAVAILABLE")
    items = []
    seen = set()
    for rec in records:
        if not isinstance(rec, dict):
            raise EvidenceError("INVALID_MANIFEST")
        rel = _relative(rec.get("path"))
        sha = rec.get("git_blob_sha1")
        size = rec.get("size")
        if str(rel) in seen:
            raise EvidenceError("DUPLICATE_PATH")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise EvidenceError("INVALID_BLOB_ID")
        if type(size) is not int or not 0 <= size <= MAX_BYTES:
            raise EvidenceError("INVALID_SIZE")
        seen.add(str(rel))
        items.append((rel, sha, size))
    matched = changed = missing = unsafe = 0
    for rel, expected, declared in items:
        try:
            fd = _open_regular_no_links(root, rel)
        except EvidenceError as exc:
            if str(exc) in ("UNSAFE_PATH", "NOT_REGULAR_FILE"):
                unsafe += 1
            else:
                missing += 1
            continue
        try:
            size = os.fstat(fd).st_size
            if size != declared or size > MAX_BYTES:
                changed += 1
                continue
            digest = hashlib.sha1()
            digest.update(f"blob {size}".encode("ascii") + bytes([0]))
            count = 0
            while True:
                data = os.read(fd, 65536)
                if not data:
                    break
                count += len(data)
                if count > MAX_BYTES:
                    break
                digest.update(data)
            if count == size and digest.hexdigest() == expected:
                matched += 1
            else:
                changed += 1
        except OSError:
            unsafe += 1
        finally:
            os.close(fd)
    return {"checked":len(items),"matched":matched,"changed":changed,
            "missing":missing,"unsafe":unsafe,"source_bytes_identical":matched==len(items),
            "original_100_requirement_acceptance":"NOT_DETERMINED"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--manifest", type=Path,
                   default=Path("docs/evidence/OMEGA_058_SOURCE_GIT_BLOBS.json"))
    args = p.parse_args(argv)
    try:
        if args.manifest.stat().st_size > 65536:
            raise EvidenceError("INVALID_MANIFEST")
        result = verify(args.root, json.loads(args.manifest.read_text(encoding="utf-8")))
    except (EvidenceError, ValueError, OSError, UnicodeError, TypeError):
        print('{"source_bytes_identical":false,"error":"SOURCE_INTEGRITY_UNVERIFIED"}')
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["source_bytes_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
