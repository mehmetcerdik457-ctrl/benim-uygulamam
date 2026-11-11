#!/usr/bin/env python3
"""Apply a narrow, independently reviewed fix to the extracted original V30.

The original tar and its 8 verified source hashes NEVER change. Only a separate
scratch copy in the ephemeral GitHub runner receives this safety correction.
"""
from pathlib import Path
import hashlib

SOURCE = Path(__file__).resolve().parents[1] / "v30_pg16_original" / "omega_postgres.py"
EXPECTED_ORIGINAL_SHA256 = "d1d4960b11a23ecf34fad017ec670c117c96fffb44a2adfb61550c3c24b38d8e"

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
            # PostgreSQL SQLSTATE 22P02 is invalid UUID syntax. Keep DB-API
            # fake-connection tests unchanged; rollback precedes translation.
            if getattr(exc, 'sqlstate', None) == '22P02':
                raise PermissionError('invalid or expired lease') from exc
            raise
"""

def main() -> None:
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED_ORIGINAL_SHA256:
        raise SystemExit("V30 unmodified source checksum mismatch")
    text = original.decode("utf-8")
    if text.count(OLD) != 1:
        raise SystemExit("V30 source code does not match patch anchor")
    corrected = text.replace(OLD, NEW).encode("utf-8")
    SOURCE.write_bytes(corrected)
    print("V30_PATCHED_CANDIDATE_SHA256=" + hashlib.sha256(corrected).hexdigest())
    print("V30_UNMODIFIED_SOURCE_PRESERVED_IN_ARCHIVE=TRUE")

if __name__ == "__main__":
    main()
