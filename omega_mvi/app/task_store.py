"""Minimal demo-only PostgreSQL task persistence; never log DSN or raw exceptions."""
import uuid
import psycopg


class DatabaseUnavailable(RuntimeError):
    pass


def _connect(dsn):
    if not dsn:
        raise DatabaseUnavailable("demo database not configured")
    try:
        return psycopg.connect(dsn, connect_timeout=3)
    except psycopg.Error:
        raise DatabaseUnavailable("demo database unavailable") from None


def create_task(dsn: str, owner: str, trace_id: str, metadata: dict) -> dict:
    if not owner.startswith("demo-") or not trace_id.startswith("demo-"):
        raise ValueError("demo identifiers required")
    task_id = uuid.uuid4()
    try:
        with _connect(dsn) as conn:
            row = conn.execute(
                """INSERT INTO omega_tasks(task_id,owner,trace_id,metadata)
                   VALUES (%s,%s,%s,%s::jsonb)
                   RETURNING task_id,owner,state,trace_id,created_at,updated_at""",
                (task_id, owner, trace_id, __import__("json").dumps(metadata)),
            ).fetchone()
            return _serialize(row)
    except psycopg.Error:
        raise DatabaseUnavailable("demo database unavailable or schema not migrated") from None


def get_task(dsn: str, task_id: uuid.UUID) -> dict | None:
    try:
        with _connect(dsn) as conn:
            row = conn.execute(
                """SELECT task_id,owner,state,trace_id,created_at,updated_at
                   FROM omega_tasks WHERE task_id = %s""", (task_id,),
            ).fetchone()
            return _serialize(row) if row else None
    except psycopg.Error:
        raise DatabaseUnavailable("demo database unavailable or schema not migrated") from None


def _serialize(row):
    return dict(zip(("task_id","owner","state","trace_id","created_at","updated_at"),
                    (str(row[0]), row[1], row[2], row[3], row[4].isoformat(), row[5].isoformat())))
