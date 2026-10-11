"""OMEGA-053: real PostgreSQL constraints; permissions are inert until IdP exists."""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
import psycopg
from db import store
from db.migrate import apply, assert_disposable_target

@pytest.fixture
def db():
    url=os.environ.get("OMEGA_DATABASE_URL")
    marker=os.environ.get("OMEGA_TEST_DB_SENTINEL")
    if not url or not marker:
        if os.environ.get("OMEGA_REQUIRE_REAL_DB")=="1":
            pytest.fail("real PostgreSQL required; no skip in authoritative job")
        pytest.skip("separate real PostgreSQL integration job required")
    with psycopg.connect(url,autocommit=True,connect_timeout=3) as conn:
        assert_disposable_target(url,marker,conn)
        apply(conn,"down",database_url=url,sentinel=marker)
        assert apply(conn,"up",database_url=url,sentinel=marker) is True
        yield conn
        apply(conn,"down",database_url=url,sentinel=marker)

def test_v3_migration_and_idempotent_rollback(db):
    url=os.environ["OMEGA_DATABASE_URL"]; marker=os.environ["OMEGA_TEST_DB_SENTINEL"]
    assert [r[0] for r in db.execute("SELECT version FROM omega_schema_version ORDER BY version")]==[1,2,3]
    assert apply(db,"up",database_url=url,sentinel=marker) is False
    assert apply(db,"down",database_url=url,sentinel=marker) is True
    assert apply(db,"down",database_url=url,sentinel=marker) is False
    assert apply(db,"up",database_url=url,sentinel=marker) is True

def test_stored_budget_scopes_and_utc_deadline(db):
    deadline=datetime.now(timezone.utc)+timedelta(hours=3)
    task=store.create(db,"tenant-a",uuid4(),{"label":"synthetic"},
                      budget_limit_minor=1200,budget_currency="TRY",
                      permissions=("inventory:read",),deadline_utc=deadline)
    value=store.get(db,task,owner="tenant-a")
    assert value["budget_limit_minor"]==1200
    assert value["budget_currency"]=="TRY"
    assert value["permissions"]==["inventory:read"]
    assert value["deadline_utc"].astimezone(timezone.utc)==deadline
    assert store.get(db,task,owner="tenant-b") is None
    assert value["state"]=="CREATED"  # does not implicitly RUN

def test_invalid_budget_permission_deadline_contract_rejected(db):
    bad=[
        {"budget_limit_minor":-1},
        {"budget_limit_minor":True},
        {"budget_limit_minor":1.5},
        {"permissions":("execute:write",)},
        {"permissions":("inventory:read","inventory:read")},
        {"budget_currency":"BTC"},
        {"deadline_utc":datetime.now(timezone.utc)-timedelta(minutes=1)},
        {"deadline_utc":datetime.now()+timedelta(hours=1)},
        {"deadline_utc":datetime.now(timezone.utc)+timedelta(days=366)},
    ]
    for fields in bad:
        with pytest.raises(ValueError):
            store.create(db,"tenant-a",uuid4(),{"label":"synthetic"},**fields)

def test_real_database_constraints_reject_direct_invalid_sql(db):
    task=store.create(db,"tenant-a",uuid4())
    for sql in (
        "UPDATE omega_tasks SET budget_limit_minor=-1 WHERE task_id=%s",
        "UPDATE omega_tasks SET permissions=ARRAY['execute:write']::text[] WHERE task_id=%s",
        "UPDATE omega_tasks SET deadline_utc=created_at - interval '1 minute' WHERE task_id=%s",
        "UPDATE omega_tasks SET deadline_utc=NULL WHERE task_id=%s",
    ):
        with pytest.raises(psycopg.Error):
            db.execute(sql,(task,))
    assert store.get(db,task)["budget_limit_minor"]==0
    assert store.get(db,task)["permissions"]==[]
    assert store.get(db,task)["state"]=="CREATED"
