"""Versioned, transactional migrations ONLY for the sentinel-verified CI demo DB.

Never supply production credentials. The sentinel is written by an independent CI step,
not by this module, and MUST exist before any migration/DDL, including DOWN.
"""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import hmac
import os
import sys

import psycopg

MIGRATIONS = Path(__file__).with_name("migrations")
VERSION = 4


def assert_disposable_target(database_url, sentinel, connection):
    """Fail BEFORE destructive SQL unless URL AND database-issued nonce match."""
    try:
        parsed = urlsplit(database_url)
        dbname = unquote(parsed.path.lstrip("/"))
        good = (
            parsed.scheme in ("postgresql", "postgres")
            and parsed.hostname == "db"
            and parsed.username == "omega_demo"
            and dbname == "omega_demo"
            and parsed.port in (None, 5432)
            and not parsed.fragment
        )
    except (AttributeError, TypeError, ValueError):
        good = False
    if not good or not isinstance(sentinel, str) or len(sentinel) != 32:
        raise ValueError("isolated test database URL and marker are required")
    if not all(c in "0123456789abcdef" for c in sentinel):
        raise ValueError("invalid isolated test marker")
    if connection is None:
        raise ValueError("verified database connection required")
    try:
        row = connection.execute(
            "SELECT current_database(), marker FROM omega_test_sentinel WHERE marker_id = 1"
        ).fetchone()
    except psycopg.Error as exc:
        raise ValueError("test database identity marker absent") from exc
    if row is None or row[0] != "omega_demo" or not isinstance(row[1],str) or not hmac.compare_digest(row[1],sentinel):
        raise ValueError("test database identity mismatch")
    return True


def apply(conn, direction="up", *, database_url=None, sentinel=None):
    if direction not in ("up", "down"):
        raise ValueError("direction must be up/down")
    # Safety guard is checked on EVERY operation, before any SQL write or DROP.
    assert_disposable_target(database_url, sentinel, conn)
    changed = False
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(91833711)")
            cur.execute("CREATE TABLE IF NOT EXISTS omega_schema_version(version INTEGER PRIMARY KEY)")
            cur.execute("SELECT version FROM omega_schema_version ORDER BY version DESC")
            present = {v for (v,) in cur.fetchall()}
            versions = (1, 2, 3, 4) if direction == "up" else (4, 3, 2, 1)
            for version in versions:
                if (direction == "up") == (version in present):
                    continue
                name = {1: "tasks", 2: "security", 3: "task_controls", 4: "demo_reader"}[version]
                script = MIGRATIONS / f"{version:03d}_{name}.{direction}.sql"
                cur.execute(script.read_text(encoding="utf-8"))
                if direction == "up":
                    cur.execute("INSERT INTO omega_schema_version(version) VALUES (%s)", (version,))
                else:
                    cur.execute("DELETE FROM omega_schema_version WHERE version=%s", (version,))
                changed = True
    return changed


if __name__ == "__main__":
    direction = sys.argv[1] if len(sys.argv) > 1 else "up"
    with psycopg.connect(os.environ["OMEGA_DATABASE_URL"], autocommit=True, connect_timeout=3) as conn:
        changed = apply(conn, direction,
                        database_url=os.environ.get("OMEGA_DATABASE_URL"),
                        sentinel=os.environ.get("OMEGA_TEST_DB_SENTINEL"))
    print("OMEGA_MIGRATION=" + direction + " CHANGED=" + str(changed))
