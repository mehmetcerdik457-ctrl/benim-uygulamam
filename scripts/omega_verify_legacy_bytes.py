#!/usr/bin/env python3
"""Offline, read-only byte verification for recovered PROJECT OMEGA artifacts.

A historical report, historical status or file name never proves that its
source bytes are present or correct. This verifier accepts a separate
versioned SHA-256 manifest and checks the actual files without extraction,
network access, execution of legacy content, or mutation of source data.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "omega-recovered-bytes-v1"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_ITEMS = 1000
MAX_FILE_BYTES = 4 * 1024 * 1024 * 1024


class EvidenceError(Exception):
    """Fixed public denial reason; do not echo secret-bearing exception text."""


def _relative(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise EvidenceError("INVALID_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in (".", "..", "") for part in value.split("/")):
        raise EvidenceError("INVALID_PATH")
    if str(path) != value:
        raise EvidenceError("INVALID_PATH")
    return path


def _open_regular_no_links(root: Path, relative: PurePosixPath) -> int:
    """Open every path segment via dir_fd without following symlinks.

    A name-based is_symlink precheck alone would be vulnerable to a directory
    rename race; directory handles and O_NOFOLLOW protect each traversal step.
    """
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    opened_dirs = []
    try:
        root_fd = os.open(root, directory_flags)
        opened_dirs.append(root_fd)
        for component in relative.parts[:-1]:
            child_fd = os.open(component, directory_flags, dir_fd=opened_dirs[-1])
            opened_dirs.append(child_fd)
        fd = os.open(relative.parts[-1], file_flags, dir_fd=opened_dirs[-1])
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise EvidenceError("NOT_REGULAR_FILE")
        return fd
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            # Includes symlinked ancestors and unsafe intermediate components.
            raise EvidenceError("UNSAFE_PATH") from None
        raise EvidenceError("FILE_UNAVAILABLE") from None
    finally:
        for dfd in reversed(opened_dirs):
            os.close(dfd)


def _sha256_fd(fd: int) -> str:
    digest = hashlib.sha256()
    length = 0
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return digest.hexdigest()
        length += len(chunk)
        if length > MAX_FILE_BYTES:
            raise EvidenceError("FILE_LIMIT_EXCEEDED")
        digest.update(chunk)


def verify(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify every listed artifact, including the source archive itself.

    Returns counts, never raw source content or unchecked historical DONE claims.
    """
    if manifest.get("schema") != SCHEMA or not isinstance(manifest.get("items"), list):
        raise EvidenceError("INVALID_MANIFEST")
    records = manifest["items"]
    if not 1 <= len(records) <= MAX_ITEMS:
        raise EvidenceError("INVALID_MANIFEST")
    version = manifest.get("source_version")
    if not isinstance(version, str) or re.fullmatch(r"[A-Za-z0-9._-]{1,80}", version) is None:
        raise EvidenceError("INVALID_SOURCE_VERSION")
    if not root.is_dir() or root.is_symlink():
        raise EvidenceError("ROOT_UNAVAILABLE")
    # Validate the entire manifest before opening even the first data file.
    seen: set[str] = set()
    entries: list[tuple[PurePosixPath, str]] = []
    for rec in records:
        if not isinstance(rec, dict):
            raise EvidenceError("INVALID_MANIFEST")
        sha = rec.get("sha256")
        if not isinstance(sha, str) or HEX256.fullmatch(sha) is None:
            raise EvidenceError("INVALID_SHA256")
        rel = _relative(rec.get("relative_path"))
        if str(rel) in seen:
            raise EvidenceError("DUPLICATE_PATH")
        seen.add(str(rel))
        entries.append((rel, sha))

    checked = matched = missing = mismatch = unsafe = 0
    for rel, sha in entries:
        checked += 1
        try:
            fd = _open_regular_no_links(root, rel)
            try:
                actual = _sha256_fd(fd)
            finally:
                os.close(fd)
        except EvidenceError as exc:
            if str(exc) in ("UNSAFE_PATH", "NOT_REGULAR_FILE", "FILE_LIMIT_EXCEEDED"):
                unsafe += 1
            else:
                missing += 1
            continue
        if actual == sha:
            matched += 1
        else:
            mismatch += 1
    return {
        "schema": SCHEMA,
        "source_version": version,
        "files_checked": checked,
        "files_matched": matched,
        "files_missing": missing,
        "files_mismatched": mismatch,
        "files_unsafe": unsafe,
        "byte_integrity_passed": checked == matched and missing == mismatch == unsafe == 0,
        "original_requirement_acceptance": "NOT_DETERMINED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline recovered-artifact SHA-256 verification")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        # Manifest is small metadata only; never interpret or execute entries.
        if args.manifest.stat().st_size > 1024 * 1024:
            raise EvidenceError("INVALID_MANIFEST")
        with args.manifest.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
        if not isinstance(manifest, dict):
            raise EvidenceError("INVALID_MANIFEST")
        outcome = verify(args.root, manifest)
    except (EvidenceError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        # Do not expose arbitrary filesystem paths or traceback details.
        print(json.dumps({"byte_integrity_passed": False, "error": "VERIFICATION_FAILED"}))
        return 2
    print(json.dumps(outcome, sort_keys=True, separators=(",", ":")))
    return 0 if outcome["byte_integrity_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
