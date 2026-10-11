"""REAL PostgreSQL CI tests; require isolated OMEGA_DATABASE_URL."""
import os
from uuid import uuid4
import pytest
import psycopg
from fastapi.testclient import TestClient
from db.migrate import apply
from db import store
from db.test_api import factory

@pytest.fixture
def connection():
    url=os.environ.get("OMEGA_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL endpoint missing: no DB integration acceptance")
    with psycopg.connect(url,autocommit=True,connect_timeout=3) as conn:
        apply(conn,"down")
        apply(conn,"up")
        yield conn
        apply(conn,"down")

def test_migration_roundtrip_and_idempotence(connection):
    assert apply(connection,"up") is False
    assert connection.execute("SELECT version FROM omega_schema_version").fetchone()==(1,)
    assert apply(connection,"down") is True
    assert apply(connection,"down") is False
    assert apply(connection,"up") is True

def test_persistent_create_read_and_transitions(connection):
    tid=store.create(connection,"fixture-owner",uuid4(),{"label":"mock"})
    assert store.get(connection,tid)["state"]=="CREATED"
    with pytest.raises(psycopg.Error):
        store.advance(connection,tid,"SUCCEEDED")
    store.advance(connection,tid,"PLANNED")
    store.advance(connection,tid,"APPROVAL_PENDING")
    with pytest.raises(psycopg.Error):
        store.advance(connection,tid,"RUNNING")
    assert store.get(connection,tid)["state"]=="APPROVAL_PENDING"
    store.advance(connection,tid,"RUNNING","test-only-owner-approval-reference")
    store.advance(connection,tid,"VERIFYING")
    store.advance(connection,tid,"SUCCEEDED")
    assert connection.execute("SELECT count(*) FROM omega_task_events WHERE task_id=%s",(tid,)).fetchone()[0]==5

def test_direct_update_rejected_and_integrity(connection):
    tid=store.create(connection,"fixture-owner",uuid4())
    with pytest.raises(psycopg.Error):
        connection.execute("UPDATE omega_tasks SET state='RUNNING' WHERE task_id=%s",(tid,))
    assert store.get(connection,tid)["state"]=="CREATED"
    with pytest.raises(ValueError):
        store.create(connection,"fixture-owner",uuid4(),{"secret":"never-index"})

def test_live_api_create_and_get_and_fail_closed(connection):
    app=factory(os.environ["OMEGA_DATABASE_URL"])
    client=TestClient(app)
    trace=str(uuid4())
    response=client.post("/demo/tasks",json={"owner":"fixture-owner","trace_id":trace,"label":"synthetic"})
    assert response.status_code==201,response.text
    tid=response.json()["task_id"]
    got=client.get("/demo/tasks/"+tid)
    assert got.status_code==200 and got.json()["state"]=="CREATED"
    assert got.json()["trace_id"]==trace
    closed=TestClient(factory("postgresql://127.0.0.1:1/doesnotexist"))
    assert closed.get("/demo/tasks/"+tid).status_code==503
