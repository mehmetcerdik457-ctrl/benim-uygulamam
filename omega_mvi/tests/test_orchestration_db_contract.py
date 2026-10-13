"""OMEGA-053/059: ONLY isolated sentinel-verified real PostgreSQL evidence.

This checks durable metadata, read-by-owner, append-only event transitions,
and the disabled execution gate. The offline orchestrator is not linked to DB.
"""
import os
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import pytest
import psycopg  # Required in the authoritative disposable-DB job; missing driver must FAIL.
from db import store
from db.migrate import apply, assert_disposable_target


@pytest.fixture
def disposable_db():
    url = os.environ.get("OMEGA_DATABASE_URL")
    sentinel = os.environ.get("OMEGA_TEST_DB_SENTINEL")
    if not url or not sentinel:
        if os.environ.get("OMEGA_REQUIRE_REAL_DB") == "1":
            pytest.fail("real disposable PostgreSQL is required for authoritative verification")
        pytest.skip("no disposable PostgreSQL; local offline tests are not DB evidence")
    with psycopg.connect(url, autocommit=True, connect_timeout=3) as conn:
        assert_disposable_target(url, sentinel, conn)
        apply(conn, "down", database_url=url, sentinel=sentinel)
        apply(conn, "up", database_url=url, sentinel=sentinel)
        yield conn
        apply(conn, "down", database_url=url, sentinel=sentinel)


def test_durable_controls_owner_isolation_trace_and_append_only_audit(disposable_db):
    conn = disposable_db
    trace = uuid4()
    deadline = datetime.now(timezone.utc) + timedelta(minutes=20)
    task_id = store.create(conn, "fixture-owner", trace,
                           {"kind": "mock", "source": "synthetic"},
                           budget_limit_minor=17, budget_currency="TRY",
                           permissions=("rag:read", "pr:read"), deadline_utc=deadline)
    task = store.get(conn, task_id, owner="fixture-owner")
    assert task["owner"] == "fixture-owner"
    assert task["trace_id"] == trace
    assert task["budget_limit_minor"] == 17
    assert task["budget_currency"] == "TRY"
    assert task["permissions"] == ["rag:read", "pr:read"]
    assert task["deadline_utc"].astimezone(timezone.utc) == deadline
    assert store.get(conn, task_id, owner="other-fixture") is None

    assert store.advance(conn, task_id, "PLANNED") == "PLANNED"
    assert store.advance(conn, task_id, "APPROVAL_PENDING") == "APPROVAL_PENDING"
    # Arbitrary string approval cannot start live work.
    with pytest.raises(psycopg.Error):
        store.advance(conn, task_id, "RUNNING", "owner-says-yes")
    assert store.advance(conn, task_id, "CANCELLED") == "CANCELLED"
    rows = conn.execute(
        "SELECT from_state,to_state,approved_by FROM public.omega_task_events "
        "WHERE task_id=%s ORDER BY id", (task_id,)
    ).fetchall()
    assert rows == [("CREATED", "PLANNED", None),
                    ("PLANNED", "APPROVAL_PENDING", None),
                    ("APPROVAL_PENDING", "CANCELLED", None)]
    with pytest.raises(psycopg.Error):
        conn.execute("DELETE FROM public.omega_task_events WHERE task_id=%s", (task_id,))
    assert store.get(conn, task_id)["state"] == "CANCELLED"
