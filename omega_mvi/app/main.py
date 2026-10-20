"""OMEGA Phase 0 demonstration: health only, no provider integrations."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="OMEGA demo", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "service": "omega-mvi-demo",
        "status": "ok",
        "mode": "mock",
        "production_ready": False,
        "external_api_enabled": False,
        "owner_hardware": "UNKNOWN",
        "database_migrations_ready": False,
    }


@app.get("/api/readiness")
def readiness():
    return {"production_ready": False, "reasons": ["phase_0_unaccepted", "mvi_unverified"]}


@app.post("/api/chat")
@app.post("/api/execute")
def disabled_operations():
    raise HTTPException(status_code=403, detail="DENIED: not enabled")


from pathlib import Path
from fastapi.responses import FileResponse

@app.get("/",include_in_schema=False)
def turkish_dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html",
                        media_type="text/html",
                        headers={"Cache-Control":"no-store","Content-Security-Policy":"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'","Referrer-Policy":"no-referrer","X-Frame-Options":"DENY","X-Content-Type-Options":"nosniff"})


# Fixed synthetic-only demo routes. Not an authenticated task API or model runtime.
import os
from urllib.parse import urlsplit
import psycopg

@app.get("/api/demo/inspection", include_in_schema=False)
def demo_inspection():
    from omega_mvi.inspection.pipeline import inspect_offline_fixture
    return inspect_offline_fixture()

@app.get("/api/demo/task-status", include_in_schema=False)
def demo_task_status():
    # Never reveal owner, trace_id, task_id, metadata, or per-task permissions.
    if os.environ.get("OMEGA_DEMO_READS_ENABLED") != "true" or os.environ.get("OMEGA_MODE") != "mock":
        raise HTTPException(status_code=403, detail="DEMO_READ_DISABLED")
    uri=os.environ.get("OMEGA_DEMO_READER_URL","")
    try:
        parsed=urlsplit(uri)
        if not (parsed.scheme in ("postgresql","postgres")
                and parsed.hostname=="db" and parsed.port in (None,5432)
                and parsed.username=="omega_demo_reader"
                and parsed.path=="/omega_demo" and parsed.password):
            raise ValueError("invalid demo reader URI")
        # Runtime reader is granted SELECT on an aggregate view ONLY.
        # Session read-only is defense-in-depth, never authorization.
        with psycopg.connect(uri, autocommit=True, connect_timeout=3,
                             options="-c default_transaction_read_only=on") as conn:
            who, db=conn.execute("SELECT current_user,current_database()").fetchone()
            if who!="omega_demo_reader" or db!="omega_demo":
                raise ValueError("unexpected database principal")
            rows=conn.execute(
                "SELECT state,count FROM public.omega_demo_status_counts ORDER BY state"
            ).fetchall()
        allowed={"CREATED","PLANNED","APPROVAL_PENDING","RUNNING","VERIFYING","SUCCEEDED","FAILED","CANCELLED"}
        if any(state not in allowed or type(count) is not int or count<0 for state,count in rows):
            raise ValueError("unexpected DB view content")
        return {"mode":"disposable-synthetic-only","aggregate":[{"state":s,"count":v} for s,v in rows],
                "task_details_available":False,"production_ready":False}
    except (ValueError,psycopg.Error,OverflowError) as exc:
        raise HTTPException(status_code=503,detail="DEMO_DATABASE_UNAVAILABLE") from exc


# Fixed read-only static assets: no directory traversal or externally hosted scripts.
@app.get("/assets/dashboard.js", include_in_schema=False)
def dashboard_javascript():
    return FileResponse(Path(__file__).parent / "static" / "dashboard.js",
                        media_type="text/javascript",
                        headers={"Cache-Control":"no-store",
                                 "X-Content-Type-Options":"nosniff",
                                 "Cross-Origin-Resource-Policy":"same-origin"})

@app.get("/assets/dashboard.css", include_in_schema=False)
def dashboard_stylesheet():
    return FileResponse(Path(__file__).parent / "static" / "dashboard.css",
                        media_type="text/css",
                        headers={"Cache-Control":"no-store",
                                 "X-Content-Type-Options":"nosniff",
                                 "Cross-Origin-Resource-Policy":"same-origin"})
