"""OMEGA Phase 0 demonstration: health only, no provider integrations."""

from fastapi import FastAPI, HTTPException
from omega_mvi.inspection.service import build_synthetic_snapshot

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


@app.get("/api/inspection/demo")
def synthetic_inspection():
    try:
        return build_synthetic_snapshot()
    except Exception:
        raise HTTPException(status_code=503, detail="Synthetic inspection unavailable") from None


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
                        headers={"Cache-Control":"no-store","Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'none'; frame-ancestors 'none'","X-Content-Type-Options":"nosniff"})
