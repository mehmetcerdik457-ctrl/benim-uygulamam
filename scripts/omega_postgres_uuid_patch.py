#!/usr/bin/env python3
"""Canonical PostgreSQL UUID lease-token error patch shared by V30 and V34 CI."""
from pathlib import Path
import hashlib

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
            # PostgreSQL SQLSTATE 22P02 is malformed UUID input. The transaction
            # context rolls back before this narrow translation; other errors propagate.
            if getattr(exc, 'sqlstate', None) == '22P02':
                raise PermissionError('invalid or expired lease') from exc
            raise
"""

def apply(source: Path, expected_sha256: str) -> str:
    original = source.read_bytes()
    actual = hashlib.sha256(original).hexdigest()
    if actual != expected_sha256:
        raise SystemExit(f"original source checksum mismatch: {actual}")
    text = original.decode("utf-8")
    if text.count(OLD) != 1:
        raise SystemExit("canonical patch anchor absent or ambiguous")
    patched = text.replace(OLD, NEW).encode("utf-8")
    source.write_bytes(patched)
    digest = hashlib.sha256(patched).hexdigest()
    print("OMEGA_CANONICAL_UUID_PATCH_SHA256=" + digest)
    return digest
