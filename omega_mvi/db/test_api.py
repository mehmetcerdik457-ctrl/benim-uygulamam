"""Opt-in CI-only API factory. Never mount on normal application."""
from uuid import UUID
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import psycopg
from db import store

class DemoTask(BaseModel):
    owner: str=Field(min_length=1,max_length=128)
    trace_id: UUID
    label: str=Field(min_length=1,max_length=100)

def factory(database_url):
    app=FastAPI(docs_url=None,openapi_url=None,redoc_url=None)
    @app.post("/demo/tasks",status_code=201)
    def create_task(request:DemoTask):
        try:
            with psycopg.connect(database_url,autocommit=True,connect_timeout=3) as conn:
                task_id=store.create(conn,request.owner,request.trace_id,{"label":request.label})
            return {"task_id":str(task_id),"state":"CREATED"}
        except psycopg.Error:
            raise HTTPException(status_code=503,detail="database unavailable")
    @app.get("/demo/tasks/{task_id}")
    def read_task(task_id:UUID):
        try:
            with psycopg.connect(database_url,autocommit=True,connect_timeout=3) as conn:
                item=store.get(conn,task_id)
            if not item: raise HTTPException(status_code=404,detail="not found")
            return {"task_id":str(item["task_id"]),"state":item["state"],"owner":item["owner"],"trace_id":str(item["trace_id"])}
        except psycopg.Error:
            raise HTTPException(status_code=503,detail="database unavailable")
    return app
