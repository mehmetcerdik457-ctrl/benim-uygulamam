#!/usr/bin/env python3
"""SHA-pinned V34 original-source replay. Never authorizes paid entitlements.

The only candidate change is PostgreSQL SQLSTATE 22P02 lease error mapping,
made in an ephemeral extracted copy. Source-only archive excludes owner documents.
"""
from __future__ import annotations

import base64
import brotli
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "v34_source_run"
ARCHIVE = ROOT / "evidence" / "omega_v34_sourceonly.tar.br.b64"
MANIFEST = ROOT / "evidence" / "omega_v34_source_manifest.json"
ORIGINAL_QUEUE_HASH = "d1d4960b11a23ecf34fad017ec670c117c96fffb44a2adfb61550c3c24b38d8e"
PATCHED_QUEUE_HASH = "3a8a40089a6f9d2a72c2ffb220052cdf427d8677897f936fc5fb4eec5f22c88a"
ALLOWED_DSN = "postgresql://omega_v34:ci-ephemeral-only@127.0.0.1:5432/omega_test_v34"

OLD = """        with self.db.transaction():
            row = self.db.execute('''UPDATE omega_jobs SET status=%s,token=NULL,expires=NULL
                WHERE id=%s AND token=%s AND status='LEASED' AND expires>now()
                RETURNING id''', ('DONE' if success else 'FAILED', ident, token)).fetchone()
            if not row:
                raise PermissionError('invalid or expired lease')
"""
NEW = """        try:
            with self.db.transaction():
                row = self.db.execute('''UPDATE omega_jobs SET status=%s,token=NULL,expires=NULL
                    WHERE id=%s AND token=%s AND status='LEASED' AND expires>now()
                    RETURNING id''', ('DONE' if success else 'FAILED', ident, token)).fetchone()
                if not row:
                    raise PermissionError('invalid or expired lease')
        except Exception as exc:
            # SQLSTATE 22P02: reject malformed UUID lease tokens; other errors stay intact.
            if getattr(exc, 'sqlstate', None) == '22P02':
                raise PermissionError('invalid or expired lease') from exc
            raise
"""


def verify_environment(mode: str) -> None:
    dsn = os.environ.get("OMEGA_TEST_POSTGRES_DSN")
    if mode == "--baseline":
        if dsn or os.environ.get("OMEGA_TEST_ALLOW_DESTRUCTIVE"):
            raise RuntimeError("offline baseline cannot use a PostgreSQL DSN")
        return
    if dsn != ALLOWED_DSN or os.environ.get("OMEGA_TEST_ALLOW_DESTRUCTIVE") != "YES":
        raise RuntimeError("only exact disposable CI PostgreSQL DSN is allowed")
    parsed = urlsplit(dsn)
    if parsed.hostname != "127.0.0.1" or parsed.port != 5432 or parsed.query or parsed.fragment:
        raise RuntimeError("invalid test DB destination")
    import psycopg
    with psycopg.connect(dsn) as con:
        row = con.execute(
            "SELECT current_database(), current_user, "
            "(SELECT rolsuper FROM pg_roles WHERE rolname=current_user), "
            "has_database_privilege(current_user, current_database(), 'CREATE')"
        ).fetchone()
        if row != ("omega_test_v34", "omega_v34", False, True):
            raise RuntimeError("unexpected PostgreSQL identity or privileges")
    print("V34_ISOLATED_NON_SUPERUSER_DB=PASS", flush=True)


def reconstruct() -> None:
    if ARCHIVE.is_symlink() or MANIFEST.is_symlink():
        raise RuntimeError("source input must not be symlinked")
    catalog = json.loads(MANIFEST.read_text("utf-8"))
    expected = catalog["source_manifest"]
    inventory = {entry["path"]: entry for entry in expected}
    if len(inventory) != len(expected) or len(inventory) != 60 or catalog["original_manifest_files"] != 62:
        raise RuntimeError("V34 original manifest inventory mismatch")
    chunks = ARCHIVE.read_text("ascii").splitlines()
    if not chunks or len(chunks) > 12 or any(not re.fullmatch(r"[A-Za-z0-9+/]{1,4800}={0,2}", c) for c in chunks):
        raise RuntimeError("bad source-only base64 text")
    packed = base64.b64decode("".join(chunks), validate=True)
    if hashlib.sha256(packed).hexdigest() != catalog["compressed_tar_sha256"]:
        raise RuntimeError("source archive sha256 mismatch")
    raw = brotli.decompress(packed)
    if len(raw) > 400_000:
        raise RuntimeError("source archive expansion exceeds bound")
    if DEST.exists():
        raise RuntimeError("extract destination already exists; fail closed")
    DEST.mkdir()
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as bundle:
        for member in bundle:
            if (not member.isfile() or member.size > 25_000
                    or member.name not in inventory or member.name in seen
                    or not re.fullmatch(r"(?:tests/)?[A-Za-z0-9_.-]+(?:\.py|\.sql|\.yaml)", member.name)):
                raise RuntimeError("unauthorized original source entry")
            data = bundle.extractfile(member).read()
            expected_file = inventory[member.name]
            if len(data) != member.size or len(data) != expected_file["bytes"] or hashlib.sha256(data).hexdigest() != expected_file["sha256"]:
                raise RuntimeError("original V34 file sha256/length mismatch")
            target = DEST / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                raise RuntimeError("original source extraction collision")
            target.write_bytes(data)
            seen.add(member.name)
    if seen != set(inventory):
        raise RuntimeError("missing original V34 source members")
    if hashlib.sha256((DEST / "omega_postgres.py").read_bytes()).hexdigest() != ORIGINAL_QUEUE_HASH:
        raise RuntimeError("original queue source differs from V30 baseline")
    print("V34_ORIGINAL_SOURCE_60_SHA256=PASS", flush=True)


def apply_candidate_fix() -> None:
    path = DEST / "omega_postgres.py"
    source = path.read_text("utf-8")
    if source.count(OLD) != 1:
        raise RuntimeError("patch anchor is absent or ambiguous")
    corrected = source.replace(OLD, NEW).encode("utf-8")
    if hashlib.sha256(corrected).hexdigest() != PATCHED_QUEUE_HASH:
        raise RuntimeError("V34 candidate checksum mismatch")
    path.write_bytes(corrected)
    print("V34_PATCHED_QUEUE_SHA256=" + PATCHED_QUEUE_HASH, flush=True)


def execute(mode: str) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],
                       cwd=DEST,env=env,capture_output=True,text=True,timeout=220)
    output = r.stdout + r.stderr
    print(output,flush=True)
    test_count = re.search(r"(?m)^Ran (\d+) tests in ",output)
    skips = len(re.findall(r"\.\.\. skipped ",output))
    count = int(test_count.group(1)) if test_count else -1
    if mode == "--baseline":
        good = r.returncode == 0 and count == 354 and skips == 16 and bool(re.search(r"(?m)^OK \(skipped=16\)$",output))
        print("V34_ORIGINAL_BASELINE="+("338_PASS_16_SKIP" if good else "NOT_ACCEPTED"),flush=True)
    else:
        good = r.returncode == 0 and count == 354 and skips == 0 and bool(re.search(r"(?m)^OK$",output)) and "FAILED (" not in output
        print("V34_PATCHED_FULL_354="+("354_PASS_0_SKIP" if good else "NOT_ACCEPTED"),flush=True)
        print("ORBA_REAL_PLAY_PURCHASES=NOT_VERIFIED",flush=True)
        print("ORBA_PRODUCTION_REVENUE=NOT_DEPLOYED",flush=True)
    if not good: raise RuntimeError("exact V34 test acceptance criteria not met")


def main() -> None:
    if sys.argv[1:] not in (["--baseline"],["--live"]):
        raise RuntimeError("expected --baseline or --live")
    mode = sys.argv[1]
    verify_environment(mode)
    reconstruct()
    if mode == "--live": apply_candidate_fix()
    execute(mode)

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(type(exc).__name__+": "+str(exc),file=sys.stderr)
        sys.exit(2)
