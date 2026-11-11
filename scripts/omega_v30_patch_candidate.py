#!/usr/bin/env python3
"""Apply a narrow, independently reviewed fix to the extracted original V30.

The original tar and its 8 verified source hashes NEVER change. Only a separate
scratch copy in the ephemeral GitHub runner receives this safety correction.
"""
from pathlib import Path
import hashlib

SOURCE = Path(__file__).resolve().parents[1] / "v30_pg16_original" / "omega_postgres.py"
EXPECTED_ORIGINAL_SHA256 = "d1d4960b11a23ecf34fad017ec670c117c96fffb44a2adfb61550c3c24b38d8e"

OLD = """    def complete(self, ident, token, success=True):
        if type(success) is not bool or not isinstance(token, str) or not token:
            raise ValueError('invalid completion')
        with self.db.transaction():
"""
NEW = """    def complete(self, ident, token, success=True):
        if type(success) is not bool or not isinstance(token, str) or not token:
            raise ValueError('invalid completion')
        # PostgreSQL stores UUID leases. A malformed untrusted token must be
        # rejected BEFORE SQL; do not leak psycopg InvalidTextRepresentation.
        # Keep the original valid-token path and lease checks unchanged.
        try:
            uuid.UUID(str(ident))
            uuid.UUID(token)
        except (TypeError, AttributeError, ValueError) as exc:
            raise PermissionError('invalid or expired lease') from exc
        with self.db.transaction():
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
