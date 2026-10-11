"""DB tasks are deterministic metadata only. No secret values or model outputs."""
from uuid import uuid4
from psycopg.types.json import Jsonb

VALID_STATES={"CREATED","PLANNED","APPROVAL_PENDING","RUNNING","VERIFYING","SUCCEEDED","FAILED","CANCELLED"}

def create(conn, owner, trace_id, metadata=None):
    if not isinstance(owner,str) or not 1<=len(owner)<=128:
        raise ValueError("invalid owner")
    data=metadata or {}
    if not isinstance(data,dict) or any(k not in {"kind","label","source"} for k in data):
        raise ValueError("unsupported task metadata keys")
    task_id=uuid4()
    with conn.transaction():
        conn.execute("INSERT INTO omega_tasks(task_id,owner,trace_id,metadata) VALUES (%s,%s,%s,%s)",
                     (task_id,owner,trace_id,Jsonb(data)))
    return task_id

def get(conn,task_id):
    row=conn.execute("SELECT task_id,owner,state,trace_id,metadata FROM omega_tasks WHERE task_id=%s",(task_id,)).fetchone()
    if row is None: return None
    return dict(zip(("task_id","owner","state","trace_id","metadata"),row))

def advance(conn,task_id,next_state,approval=None):
    if next_state not in VALID_STATES: raise ValueError("invalid state")
    # Authorization is not a model decision. Test gate accepts only a separately
    # supplied approval reference; cryptographic owner verification is MVI-03.
    with conn.transaction():
        conn.execute("SELECT set_config('omega.transition_authorized','yes',true)")
        return conn.execute("SELECT omega_transition(%s,%s,%s)",
                            (task_id,next_state,approval)).fetchone()[0]
