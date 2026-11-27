#!/usr/bin/env python3
"""Apply the shared canonical PostgreSQL UUID lease patch to extracted V30."""
from pathlib import Path
from omega_postgres_uuid_patch import apply

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "v30_pg16_original" / "omega_postgres.py"
EXPECTED_ORIGINAL_SHA256 = "d1d4960b11a23ecf34fad017ec670c117c96fffb44a2adfb61550c3c24b38d8e"

if __name__ == "__main__":
    apply(SOURCE, EXPECTED_ORIGINAL_SHA256)
    print("V30_UNMODIFIED_SOURCE_PRESERVED_IN_ARCHIVE=TRUE")
