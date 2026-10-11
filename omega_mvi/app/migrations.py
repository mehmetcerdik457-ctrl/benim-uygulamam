"""Transactional, reversible versioned migrations for an isolated demo database."""
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def migrate(dsn: str, direction: str = "up") -> int:
    if direction not in {"up", "down"}:
        raise ValueError("invalid migration direction")
    if not dsn:
        raise RuntimeError("database DSN missing: fail closed")
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(7202602)")
            conn.execute("""CREATE TABLE IF NOT EXISTS omega_schema_migrations (
                version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
            applied = {row[0] for row in conn.execute("SELECT version FROM omega_schema_migrations")}
            versions = sorted(int(p.name.split("_")[0]) for p in MIGRATIONS.glob("*.up.sql"))
            if len(versions) != len(set(versions)):
                raise RuntimeError("duplicate migration version")
            if direction == "up":
                for version in versions:
                    if version not in applied:
                        path = next(MIGRATIONS.glob(f"{version:03d}_*.up.sql"))
                        conn.execute(path.read_text(encoding="utf-8"))
                        conn.execute("INSERT INTO omega_schema_migrations(version) VALUES (%s)", (version,))
            elif applied:
                version = max(applied)
                path = next(MIGRATIONS.glob(f"{version:03d}_*.down.sql"))
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("DELETE FROM omega_schema_migrations WHERE version = %s", (version,))
            return conn.execute("SELECT COUNT(*) FROM omega_schema_migrations").fetchone()[0]


if __name__ == "__main__":
    import os
    import sys
    mode = sys.argv[1] if len(sys.argv) == 2 else "up"
    count = migrate(os.environ.get("OMEGA_DEMO_DATABASE_URL", ""), mode)
    print(f"omega_migration_versions_applied={count}")
