"""Synthetic task storage for sentinel-verified integration tests only.

The normal application does NOT offer live task execution. No user input is
accepted as an authenticated owner. The test API supplies a server-side fixture
identity; real identity verification remains MVI-03 BLOCKED.
"""
import re
from uuid import uuid4
from psycopg.types.json import Jsonb

VALID_STATES={"CREATED","PLANNED","APPROVAL_PENDING","RUNNING","VERIFYING","SUCCEEDED","FAILED","CANCELLED"}
_ALLOWED_KIND={"mock","inventory","scheduled"}
_ALLOWED_SOURCE={"synthetic","local-fixture"}
_LABEL=re.compile(r"[A-Za-z0-9 _-]{1,100}\Z",re.ASCII)
_OWNER=re.compile(r"[A-Za-z0-9_-]{1,128}\Z",re.ASCII)

def _metadata(data):
    if not isinstance(data,dict) or any(k not in {"kind","label","source"} for k in data):
        raise ValueError("unsupported metadata")
    if any(not isinstance(v,str) for v in data.values()):
        raise ValueError("metadata must be strings")
    if "kind" in data and data["kind"] not in _ALLOWED_KIND:
        raise ValueError("invalid synthetic kind")
    if "source" in data and data["source"] not in _ALLOWED_SOURCE:
        raise ValueError("invalid synthetic source")
    if "label" in data and data["label"] not in {"mock","synthetic","safe fixture","offline fixture"}:
        raise ValueError("only predefined, nonidentifying synthetic fixture labels are accepted")
    return data

def create(conn, owner, trace_id, metadata=None):
    if not isinstance(owner,str) or _OWNER.fullmatch(owner) is None:
        raise ValueError("invalid owner")
    data=_metadata({} if metadata is None else metadata)
    task_id=uuid4()
    with conn.transaction():
        conn.execute("INSERT INTO omega_tasks(task_id,owner,trace_id,metadata) VALUES (%s,%s,%s,%s)",
                     (task_id,owner,trace_id,Jsonb(data)))
    return task_id

def get(conn,task_id,owner=None):
    if owner is None:
        row=conn.execute("SELECT task_id,owner,state,trace_id,metadata FROM omega_tasks WHERE task_id=%s",(task_id,)).fetchone()
    else:
        if not isinstance(owner,str) or _OWNER.fullmatch(owner) is None:
            raise ValueError("invalid verified owner")
        row=conn.execute("SELECT task_id,owner,state,trace_id,metadata FROM omega_tasks WHERE task_id=%s AND owner=%s",(task_id,owner)).fetchone()
    if row is None: return None
    return dict(zip(("task_id","owner","state","trace_id","metadata"),row))

def advance(conn,task_id,next_state,approval=None):
    if next_state not in VALID_STATES:
        raise ValueError("invalid state")
    # Untrusted settings or caller text are NEVER used to bypass SQL gate.
    with conn.transaction():
        return conn.execute("SELECT public.omega_transition(%s,%s,%s)",
                            (task_id,next_state,approval)).fetchone()[0]
