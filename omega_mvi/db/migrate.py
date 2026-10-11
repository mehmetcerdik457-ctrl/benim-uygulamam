"""Versioned and transactional demo migrations. Run only in isolated disposable DB."""
from pathlib import Path
import sys
import psycopg

MIGRATIONS=Path(__file__).with_name("migrations")

def apply(conn, direction="up"):
    if direction not in ("up","down"):
        raise ValueError("direction must be up/down")
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(91833711)")
            cur.execute("CREATE TABLE IF NOT EXISTS omega_schema_version(version INTEGER PRIMARY KEY)")
            cur.execute("SELECT version FROM omega_schema_version ORDER BY version DESC")
            existing=[v for (v,) in cur.fetchall()]
            if direction=="up":
                if 1 in existing: return False
                cur.execute((MIGRATIONS/"001_tasks.up.sql").read_text())
                cur.execute("INSERT INTO omega_schema_version(version) VALUES (1)")
            else:
                if 1 not in existing: return False
                cur.execute((MIGRATIONS/"001_tasks.down.sql").read_text())
                cur.execute("DELETE FROM omega_schema_version WHERE version=1")
            return True

if __name__=="__main__":
    import os
    direction=sys.argv[1] if len(sys.argv)>1 else "up"
    # Runtime injected by Docker; never log connection strings.
    with psycopg.connect(os.environ["OMEGA_DATABASE_URL"],autocommit=True) as connection:
        changed=apply(connection,direction)
    print("OMEGA_MIGRATION="+direction+" CHANGED="+str(changed))
