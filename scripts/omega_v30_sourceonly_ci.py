#!/usr/bin/env python3
"""Rebuild 53 byte-identical V30 test sources from SHA-pinned archive.

No payment data, no production database, no alternate source download.
"""
from __future__ import annotations
import base64
import brotli
import hashlib
import io
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'v30_pg16_original'
DIGEST = '348318d4bf8591cb0135ab7d1bb2f63eaa6ac6466f494579649f5ca2c6e0093d'
QUEUE = 'd1d4960b11a23ecf34fad017ec670c117c96fffb44a2adfb61550c3c24b38d8e'


def main():
    pieces = []
    for i in range(1, 8):
        path = ROOT / 'evidence' / f'omega_v30_sourceonly_{i:02}.b64'
        if not path.is_file() or path.is_symlink():
            raise SystemExit('missing or symlinked V30 archive chunk')
        piece = path.read_text('ascii')
        if len(piece) != (364 if i == 7 else 6000) or not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', piece):
            raise SystemExit('invalid V30 source chunk')
        pieces.append(piece)
    compressed = base64.b64decode(''.join(pieces), validate=True)
    if hashlib.sha256(compressed).hexdigest() != DIGEST:
        raise SystemExit('V30 source-only checksum mismatch')
    raw = brotli.decompress(compressed)
    if len(raw) > 300_000:
        raise SystemExit('oversized source tar')
    DEST.mkdir(exist_ok=True)
    names = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for member in archive:
            if (not member.isfile() or member.size > 15_000
                    or not re.fullmatch(r'(?:tests/)?[A-Za-z0-9_.-]+(?:\.py|\.sql|\.yaml)', member.name)
                    or member.name in names):
                raise SystemExit('unsafe V30 archive entry')
            target = DEST / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                raise SystemExit('V30 extraction collision')
            data = archive.extractfile(member).read()
            if len(data) != member.size:
                raise SystemExit('V30 extraction truncated')
            target.write_bytes(data)
            names.add(member.name)
    if len(names) != 53 or 'tests/test_postgres_live.py' not in names or 'tests/test_postgres_audit_live.py' not in names:
        raise SystemExit('V30 source inventory incomplete')
    if hashlib.sha256((DEST / 'omega_postgres.py').read_bytes()).hexdigest() != QUEUE:
        raise SystemExit('V30 original queue source checksum mismatch')
    print('V30_SOURCE_ONLY_53_SHA256_VERIFIED=TRUE')


if __name__ == '__main__':
    main()
