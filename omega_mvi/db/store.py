"""Synthetic task storage for sentinel-verified integration tests only.

The normal application does NOT offer live task execution. No user input is
accepted as an authenticated owner. The test API supplies a server-side fixture
identity; real identity verification remains MVI-03 BLOCKED.
"""
import re
from datetime import datetime, timedelta, timezone
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

READ_SCOPES=frozenset(("repository:read","inventory:read","rag:read","pr:read"))

def _controls(budget_limit_minor, budget_currency, permissions, deadline_utc):
    if type(budget_limit_minor) is not int or not 0 <= budget_limit_minor <= 1000000000:
        raise ValueError("budget must be a finite nonnegative integer in minor units")
    if budget_currency not in ("USD","TRY"):
        raise ValueError("invalid budget currency")
    if not isinstance(permissions,(list,tuple)) or any(type(p) is not str for p in permissions):
        raise ValueError("permissions must be a read-only scope sequence")
    if len(permissions)!=len(set(permissions)) or not set(permissions).issubset(READ_SCOPES):
        raise ValueError("permissions are not authorized")
    now=datetime.now(timezone.utc)
    if deadline_utc is None:
        deadline_utc=now+timedelta(hours=1)
    if not isinstance(deadline_utc,datetime) or deadline_utc.tzinfo is None or deadline_utc.utcoffset()!=timedelta(0):
        raise ValueError("deadline must be UTC timezone-aware")
    if not (now < deadline_utc <= now+timedelta(days=365)):
        raise ValueError("deadline must be in the future and within one year")
    return budget_limit_minor, budget_currency, list(permissions), deadline_utc

def create(conn, owner, trace_id, metadata=None, *, budget_limit_minor=0,
           budget_currency="USD", permissions=(), deadline_utc=None):
    if not isinstance(owner,str) or _OWNER.fullmatch(owner) is None:
        raise ValueError("invalid owner")
    data=_metadata({} if metadata is None else metadata)
    budget_limit_minor,budget_currency,permissions,deadline_utc=_controls(
        budget_limit_minor,budget_currency,permissions,deadline_utc)
    task_id=uuid4()
    with conn.transaction():
        conn.execute("""INSERT INTO omega_tasks
          (task_id,owner,trace_id,metadata,budget_limit_minor,budget_currency,permissions,deadline_utc)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (task_id,owner,trace_id,Jsonb(data),
                      budget_limit_minor,budget_currency,permissions,deadline_utc))
    return task_id

def get(conn,task_id,owner=None):
    if owner is None:
        row=conn.execute("SELECT task_id,owner,state,trace_id,metadata,budget_limit_minor,budget_currency,permissions,deadline_utc FROM omega_tasks WHERE task_id=%s",(task_id,)).fetchone()
    else:
        if not isinstance(owner,str) or _OWNER.fullmatch(owner) is None:
            raise ValueError("invalid verified owner")
        row=conn.execute("SELECT task_id,owner,state,trace_id,metadata,budget_limit_minor,budget_currency,permissions,deadline_utc FROM omega_tasks WHERE task_id=%s AND owner=%s",(task_id,owner)).fetchone()
    if row is None: return None
    return dict(zip(("task_id","owner","state","trace_id","metadata","budget_limit_minor","budget_currency","permissions","deadline_utc"),row))

def advance(conn,task_id,next_state,approval=None):
    if next_state not in VALID_STATES:
        raise ValueError("invalid state")
    # Untrusted settings or caller text are NEVER used to bypass SQL gate.
    with conn.transaction():
        return conn.execute("SELECT public.omega_transition(%s,%s,%s)",
                            (task_id,next_state,approval)).fetchone()[0]
