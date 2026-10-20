"""One live Compose integration: PostgreSQL -> restricted reader -> FastAPI -> four inspectors."""
import os
from urllib.parse import urlsplit
from uuid import uuid4
import httpx
import psycopg
from psycopg import sql
import pytest
from db import store
from db.migrate import apply, assert_disposable_target

@pytest.fixture
def ready_demo():
    url=os.environ.get("OMEGA_DATABASE_URL","")
    marker=os.environ.get("OMEGA_TEST_DB_SENTINEL","")
    pw=os.environ.get("OMEGA_DEMO_READER_PASSWORD","")
    combined=os.environ.get("OMEGA_REQUIRE_COMBINED_E2E")=="1"
    if not combined:
        pytest.skip("only dedicated real Compose E2E job accepts this test")
    if not url or not marker or len(pw)<24 or os.environ.get("OMEGA_REQUIRE_REAL_DB")!="1":
        pytest.fail("real temporary DB, independent marker and read-only password required")
    with psycopg.connect(url,autocommit=True,connect_timeout=3) as admin:
        assert_disposable_target(url,marker,admin)
        apply(admin,"down",database_url=url,sentinel=marker)
        apply(admin,"up",database_url=url,sentinel=marker)
        # Parameterized SQL identifier/quoted literal; never log the password.
        admin.execute(sql.SQL("ALTER ROLE omega_demo_reader PASSWORD {}").format(sql.Literal(pw)))
        task=store.create(admin,"fixture-owner",uuid4(),{"label":"synthetic"},budget_limit_minor=0,
                          permissions=("inventory:read",))
        yield admin,task
        apply(admin,"down",database_url=url,sentinel=marker)

def test_real_pg_via_readonly_api_and_four_modules(ready_demo):
    admin,task=ready_demo
    # Docker-internal API, NOT a mocked TestClient or forged identity.
    origin="http://api:8000"
    result=httpx.get(origin+"/api/demo/task-status",timeout=5)
    assert result.status_code==200,result.text
    body=result.json()
    assert body["mode"]=="disposable-synthetic-only"
    assert body["task_details_available"] is False
    assert any(x["state"]=="CREATED" and x["count"]>=1 for x in body["aggregate"])
    text=result.text
    assert str(task) not in text and "fixture-owner" not in text and "trace_id" not in text
    assert "metadata" not in text and "permissions" not in text
    # Both real HTTP routes must operate on the SAME started FastAPI container.
    inspection=httpx.get(origin+"/api/demo/inspection",timeout=5)
    assert inspection.status_code==200,inspection.text
    x=inspection.json()
    assert x["mode"]=="synthetic_offline_only" and x["authority"]=="none"
    assert x["redaction_applied"] is True
    assert x["sources"] and x["review"]
    assert all(c["ref"].startswith("synthetic://") for c in x["sources"])
    assert "synthetic-opaque-value" not in inspection.text
    assert httpx.post(origin+"/api/execute",json={"task_id":str(task)},timeout=5).status_code==403
    assert httpx.post(origin+"/api/chat",json={},timeout=5).status_code==403

def test_real_postgres_reader_role_cannot_read_details_or_write(ready_demo):
    admin,task=ready_demo
    parsed=urlsplit(os.environ["OMEGA_DATABASE_URL"])
    url=psycopg.conninfo.make_conninfo(os.environ["OMEGA_DATABASE_URL"],
        user="omega_demo_reader",password=os.environ["OMEGA_DEMO_READER_PASSWORD"])
    with psycopg.connect(url,autocommit=True,connect_timeout=3) as low:
        assert low.execute("SELECT current_user").fetchone()[0]=="omega_demo_reader"
        assert low.execute("SELECT count(*) FROM public.omega_demo_status_counts").fetchone()[0]>=1
        for statement,params in [
            ("SELECT metadata FROM public.omega_tasks LIMIT 1",()),
            ("SELECT * FROM public.omega_task_events",()),
            ("UPDATE public.omega_tasks SET state='RUNNING' WHERE task_id=%s",(task,)),
            ("DELETE FROM public.omega_tasks WHERE task_id=%s",(task,)),
            ("SELECT public.omega_transition(%s,'RUNNING','fake')",(task,)),
            ("CREATE TABLE public.omega_escalation (id integer)",()),
            ("SET ROLE omega_demo_migrator",()),
        ]:
            with pytest.raises(psycopg.Error):
                low.execute(statement,params)


def test_live_http_dashboard_assets_and_csp_with_real_postgres(ready_demo):
    # Uses same real PostgreSQL and same FastAPI container as owner-isolation tests.
    origin="http://api:8000"
    root=httpx.get(origin+"/",timeout=5)
    assert root.status_code==200
    assert "Türkçe güvenli müfettiş" in root.text
    assert "unsafe-inline" not in root.headers["content-security-policy"]
    assert "script-src 'self'" in root.headers["content-security-policy"]
    js=httpx.get(origin+"/assets/dashboard.js",timeout=5)
    css=httpx.get(origin+"/assets/dashboard.css",timeout=5)
    assert js.status_code==200 and css.status_code==200
    assert "textContent" in js.text and "innerHTML" not in js.text
    assert "/api/demo/task-status" in js.text
    assert "stylesheet" in root.text
    assert httpx.post(origin+"/api/execute",json={"target":"synthetic"},timeout=5).status_code==403


def test_live_fastapi_dashboard_assets_and_strict_browser_policy(ready_demo):
    """Real Docker API HTTP, not a mocked TestClient."""
    origin="http://api:8000"
    page=httpx.get(origin+"/",timeout=5)
    assert page.status_code==200
    policy=page.headers["content-security-policy"]
    assert "script-src 'self'" in policy and "style-src 'self'" in policy
    assert "unsafe-inline" not in policy
    assert page.headers["x-frame-options"]=="DENY"
    assert 'src="/assets/dashboard.js"' in page.text
    assert 'href="/assets/dashboard.css"' in page.text
    js=httpx.get(origin+"/assets/dashboard.js",timeout=5)
    css=httpx.get(origin+"/assets/dashboard.css",timeout=5)
    assert js.status_code==200 and css.status_code==200
    assert js.headers["x-content-type-options"]=="nosniff"
    assert "textContent" in js.text and "innerHTML" not in js.text
    assert "/api/demo/task-status" in js.text
    assert "/api/demo/inspection" in js.text
    assert "http://" not in js.text and "https://" not in js.text
    assert "application/javascript" in js.headers["content-type"] or "text/javascript" in js.headers["content-type"]
    assert "text/css" in css.headers["content-type"]


def test_live_docker_http_real_public_ast_and_postgres_coexist(ready_demo):
    """Same real FastAPI container used for the sentinel-verified PostgreSQL E2E."""
    origin="http://api:8000"
    indexed=httpx.get(origin+"/api/demo/source-index",timeout=5)
    assert indexed.status_code==200,indexed.text
    payload=indexed.json()
    assert payload["mode"]=="real-public-source-ast"
    assert payload["files_indexed"]==5
    assert payload["symbol_count"]>=10
    assert payload["external_calls"] is False
    assert payload["authenticated_owner"] is False
    assert payload["production_ready"] is False
    assert payload["acceptance"]=="NOT_ACCEPTED"
    # Real paths/AST edges calculated from installed code, not synthetic source fixtures.
    assert any("pipeline.py" in x["path"] and
        any(y["symbol"]=="inspect_offline_fixture" for y in x["symbols"])
        for x in payload["files"])
    assert all(len(x["sha256"])==64 and x["byte_length"]>0 for x in payload["files"])
    assert any(x["call_edges"] for x in payload["files"])
    assert "OPENAI_API_KEY" not in indexed.text
    assert "omega_demo_reader" not in indexed.text
    # In the SAME container, the PostgreSQL role is still aggregate read-only
    # and the model and task executor still reject all requests.
    db=httpx.get(origin+"/api/demo/task-status",timeout=5)
    assert db.status_code==200
    assert db.json()["task_details_available"] is False
    assert httpx.post(origin+"/api/chat",json={"message":"synthetic"},timeout=5).status_code==403
    assert httpx.post(origin+"/api/execute",json={"task":"synthetic"},timeout=5).status_code==403
