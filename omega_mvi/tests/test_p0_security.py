"""P0 acceptance contract: real PostgreSQL, disposable guard, denied identity bypass.

These tests MUST fail rather than skip when PostgreSQL is unavailable in CI.
"""
import os
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db import store
from db.migrate import assert_disposable_target, apply
from db.test_api import factory


def test_invalid_database_guard_before_any_sql():
    sentinel = "a" * 32
    for url in (
        "postgresql://omega_demo@production.example:5432/omega_demo",
        "postgresql://omega_demo@db:5432/customer_data",
        "postgresql://admin@db:5432/omega_demo",
        "postgresql://omega_demo@127.0.0.1:5432/omega_demo",
    ):
        with pytest.raises(ValueError):
            assert_disposable_target(url, sentinel, connection=None)
    with pytest.raises(ValueError):
        assert_disposable_target("postgresql://omega_demo@db:5432/omega_demo", "", None)


@pytest.fixture
def isolated_db():
    url=os.environ.get("OMEGA_DATABASE_URL")
    sentinel=os.environ.get("OMEGA_TEST_DB_SENTINEL")
    if not url or not sentinel:
        if os.environ.get("OMEGA_REQUIRE_REAL_DB")=="1":
            pytest.fail("dedicated PostgreSQL job requires disposable DB")
        pytest.skip("not an integration run: authoritative PostgreSQL job enforces no skips")
    with psycopg.connect(url,autocommit=True,connect_timeout=3) as conn:
        assert_disposable_target(url,sentinel,conn)
        apply(conn,"down",database_url=url,sentinel=sentinel)
        apply(conn,"up",database_url=url,sentinel=sentinel)
        yield conn
        apply(conn,"down",database_url=url,sentinel=sentinel)


def test_wrong_sentinel_refuses_drop(isolated_db):
    url=os.environ["OMEGA_DATABASE_URL"]
    with pytest.raises(ValueError):
        apply(isolated_db,"down",database_url=url,sentinel="f"*32)
    assert isolated_db.execute("SELECT count(*) FROM omega_schema_version").fetchone()[0]==2


def test_role_cannot_bypass_session_value_or_function(isolated_db):
    task=store.create(isolated_db,"tenant-a",uuid4())
    with isolated_db.transaction():
        isolated_db.execute("SET LOCAL ROLE omega_demo_runtime")
        # Untrusted settings do not grant any table or transition privilege.
        isolated_db.execute("SELECT set_config('omega.transition_authorized','yes',true)")
        for sql,params in [
            ("UPDATE omega_tasks SET state='SUCCEEDED' WHERE task_id=%s",(task,)),
            ("DELETE FROM omega_task_events WHERE task_id=%s",(task,)),
            ("SELECT omega_transition(%s,'PLANNED','fake-human')",(task,)),
            ("SELECT count(*) FROM omega_tasks",()),
            ("CREATE TABLE public.omega_escalation(id integer)",()),
        ]:
            with pytest.raises(psycopg.Error):
                with isolated_db.transaction():
                    isolated_db.execute(sql,params)
    assert store.get(isolated_db,task)["state"]=="CREATED"


def test_fake_and_cross_task_approval_never_start_execution(isolated_db):
    for task in (store.create(isolated_db,"tenant-a",uuid4()),store.create(isolated_db,"tenant-b",uuid4())):
        store.advance(isolated_db,task,"PLANNED")
        store.advance(isolated_db,task,"APPROVAL_PENDING")
        for approval in ("human", "test-only-owner-approval-reference",str(uuid4()),"expired", "replayed"):
            with pytest.raises(psycopg.Error):
                store.advance(isolated_db,task,"RUNNING",approval)
        assert store.get(isolated_db,task)["state"]=="APPROVAL_PENDING"


def test_api_never_accepts_client_claimed_owner(isolated_db):
    app=factory(os.environ["OMEGA_DATABASE_URL"])
    client=TestClient(app)
    request={"owner":"tenant-a","trace_id":str(uuid4()),"label":"safe fixture"}
    assert client.post("/demo/tasks",json=request).status_code in (403,422,503)
    assert client.get("/demo/tasks/"+str(uuid4())).status_code in (403,503)


def test_server_side_test_identity_prevents_cross_tenant_read(isolated_db):
    url=os.environ["OMEGA_DATABASE_URL"]
    a=TestClient(factory(url,verified_identity=lambda:"tenant-a"))
    b=TestClient(factory(url,verified_identity=lambda:"tenant-b"))
    data={"trace_id":str(uuid4()),"label":"synthetic"}
    resp=a.post("/demo/tasks",json=data)
    assert resp.status_code==201,resp.text
    task=resp.json()["task_id"]
    assert a.get("/demo/tasks/"+task).status_code==200
    assert b.get("/demo/tasks/"+task).status_code==404
    # Caller cannot forge owner on create, including by adding a request field.
    assert b.post("/demo/tasks",json={**data,"owner":"tenant-a"}).status_code==422


def test_sensitive_metadata_values_rejected(isolated_db):
    bad=["synthetic_token=invalid_test_fixture","-----BEGIN " + "PRIVATE KEY-----","Authorization: Bearer synthetic","person@example.invalid"]
    for value in bad:
        with pytest.raises(ValueError):
            store.create(isolated_db,"tenant-a",uuid4(),{"label":value})
