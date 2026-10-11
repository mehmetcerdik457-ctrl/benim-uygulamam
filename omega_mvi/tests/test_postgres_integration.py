"""Actual PostgreSQL integration: MUST fail (not skip) without disposable DB."""
import os
from uuid import uuid4
import pytest
import psycopg
from fastapi.testclient import TestClient
from db.migrate import apply, assert_disposable_target
from db import store
from db.test_api import factory

@pytest.fixture
def connection():
    url = os.environ.get("OMEGA_DATABASE_URL")
    sentinel = os.environ.get("OMEGA_TEST_DB_SENTINEL")
    if not url or not sentinel:
        if os.environ.get("OMEGA_REQUIRE_REAL_DB")=="1":
            pytest.fail("dedicated PostgreSQL CI must provide real disposable DB")
        pytest.skip("non-integration workflow: real DB assertions run only in dedicated PostgreSQL job")
    with psycopg.connect(url,autocommit=True,connect_timeout=3) as conn:
        assert_disposable_target(url,sentinel,conn)
        apply(conn,"down",database_url=url,sentinel=sentinel)
        apply(conn,"up",database_url=url,sentinel=sentinel)
        yield conn
        apply(conn,"down",database_url=url,sentinel=sentinel)

def test_migration_roundtrip_and_idempotence(connection):
    url=os.environ["OMEGA_DATABASE_URL"]
    sentinel=os.environ["OMEGA_TEST_DB_SENTINEL"]
    assert apply(connection,"up",database_url=url,sentinel=sentinel) is False
    assert [r[0] for r in connection.execute("SELECT version FROM omega_schema_version ORDER BY version").fetchall()] == [1,2]
    assert apply(connection,"down",database_url=url,sentinel=sentinel) is True
    assert apply(connection,"down",database_url=url,sentinel=sentinel) is False
    assert apply(connection,"up",database_url=url,sentinel=sentinel) is True

def test_persistent_create_read_and_transitions(connection):
    tid=store.create(connection,"fixture-owner",uuid4(),{"label":"mock"})
    assert store.get(connection,tid)["state"]=="CREATED"
    with pytest.raises(psycopg.Error):
        store.advance(connection,tid,"SUCCEEDED")
    store.advance(connection,tid,"PLANNED")
    store.advance(connection,tid,"APPROVAL_PENDING")
    with pytest.raises(psycopg.Error):
        store.advance(connection,tid,"RUNNING")
    with pytest.raises(psycopg.Error):
        store.advance(connection,tid,"RUNNING","test-only-owner-approval-reference")
    assert store.get(connection,tid)["state"]=="APPROVAL_PENDING"
    store.advance(connection,tid,"CANCELLED")
    assert connection.execute("SELECT count(*) FROM omega_task_events WHERE task_id=%s",(tid,)).fetchone()[0]==3

def test_direct_update_rejected_and_integrity(connection):
    tid=store.create(connection,"fixture-owner",uuid4())
    with pytest.raises(psycopg.Error):
        connection.execute("UPDATE omega_tasks SET state='RUNNING' WHERE task_id=%s",(tid,))
    with pytest.raises(psycopg.Error):
        connection.execute("DELETE FROM omega_task_events")
    assert store.get(connection,tid)["state"]=="CREATED"
    with pytest.raises(ValueError):
        store.create(connection,"fixture-owner",uuid4(),{"secret":"never-index"})

def test_live_api_create_and_get_and_fail_closed(connection):
    client=TestClient(factory(os.environ["OMEGA_DATABASE_URL"],verified_identity=lambda:"fixture-owner"))
    trace=str(uuid4())
    response=client.post("/demo/tasks",json={"trace_id":trace,"label":"synthetic"})
    assert response.status_code==201,response.text
    tid=response.json()["task_id"]
    got=client.get("/demo/tasks/"+tid)
    assert got.status_code==200 and got.json()["state"]=="CREATED"
    assert got.json()["trace_id"]==trace
    closed=TestClient(factory("postgresql://127.0.0.1:1/doesnotexist",verified_identity=lambda:"fixture-owner"))
    assert closed.get("/demo/tasks/"+tid).status_code==503
