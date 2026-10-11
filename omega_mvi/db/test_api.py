"""Opt-in CI-only API fixture; NOT mounted on the actual OMEGA API.

There is intentionally no client-supplied owner. A fixture identity may be
supplied SERVER-SIDE for negative tenant-isolation tests only. Without it,
requests fail closed; no real identity provider is configured.
"""
from uuid import UUID
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
import os
import psycopg
from db import store
from db.migrate import assert_disposable_target

class DemoTask(BaseModel):
    model_config=ConfigDict(extra="forbid")
    trace_id: UUID
    label: Literal["mock","synthetic","safe fixture","offline fixture"]

def factory(database_url, verified_identity=None):
    app=FastAPI(docs_url=None,openapi_url=None,redoc_url=None)
    def principal():
        # This is ONLY a deterministic test fixture; do NOT wire request
        # headers, LLM responses or user-controlled fields to it.
        if verified_identity is None:
            raise HTTPException(status_code=403,detail="verified identity unavailable")
        owner=verified_identity()
        if owner not in ("tenant-a","tenant-b","fixture-owner"):
            raise HTTPException(status_code=403,detail="verified identity unavailable")
        return owner

    @app.post("/demo/tasks",status_code=201)
    def create_task(request:DemoTask):
        owner=principal()
        try:
            with psycopg.connect(database_url,autocommit=True,connect_timeout=3) as conn:
                assert_disposable_target(database_url,os.environ.get("OMEGA_TEST_DB_SENTINEL"),conn)
                task_id=store.create(conn,owner,request.trace_id,{"label":request.label})
            return {"task_id":str(task_id),"state":"CREATED"}
        except (psycopg.Error,ValueError) as exc:
            raise HTTPException(status_code=503,detail="isolated database unavailable") from exc

    @app.get("/demo/tasks/{task_id}")
    def read_task(task_id:UUID):
        owner=principal()
        try:
            with psycopg.connect(database_url,autocommit=True,connect_timeout=3) as conn:
                assert_disposable_target(database_url,os.environ.get("OMEGA_TEST_DB_SENTINEL"),conn)
                item=store.get(conn,task_id,owner=owner)
            if not item:
                raise HTTPException(status_code=404,detail="not found")
            return {"task_id":str(item["task_id"]),"state":item["state"],"owner":item["owner"],"trace_id":str(item["trace_id"])}
        except (psycopg.Error,ValueError) as exc:
            raise HTTPException(status_code=503,detail="isolated database unavailable") from exc
    return app
