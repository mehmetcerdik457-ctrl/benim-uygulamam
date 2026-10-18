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
