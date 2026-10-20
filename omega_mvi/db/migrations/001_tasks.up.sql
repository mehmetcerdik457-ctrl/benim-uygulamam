CREATE TABLE IF NOT EXISTS omega_tasks (
 task_id UUID PRIMARY KEY,
 owner TEXT NOT NULL CHECK (length(owner) BETWEEN 1 AND 128),
 state TEXT NOT NULL DEFAULT 'CREATED' CHECK (state IN ('CREATED','PLANNED','APPROVAL_PENDING','RUNNING','VERIFYING','SUCCEEDED','FAILED','CANCELLED')),
 trace_id UUID NOT NULL,
 metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata)='object' AND pg_column_size(metadata) < 8192),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS omega_tasks_owner_idx ON omega_tasks(owner,created_at DESC);
CREATE TABLE IF NOT EXISTS omega_task_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 task_id UUID NOT NULL REFERENCES omega_tasks(task_id) ON DELETE RESTRICT,
 from_state TEXT NOT NULL,
 to_state TEXT NOT NULL,
 event_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 approved_by TEXT NULL
);
CREATE OR REPLACE FUNCTION omega_transition(p_task UUID,p_next TEXT,p_approval TEXT DEFAULT NULL)
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE old_state TEXT;
BEGIN
 SELECT state INTO old_state FROM omega_tasks WHERE task_id=p_task FOR UPDATE;
 IF old_state IS NULL THEN RAISE EXCEPTION 'task not found' USING ERRCODE='P0002'; END IF;
 IF NOT (
   (old_state='CREATED' AND p_next IN ('PLANNED','CANCELLED')) OR
   (old_state='PLANNED' AND p_next IN ('APPROVAL_PENDING','CANCELLED')) OR
   (old_state='APPROVAL_PENDING' AND p_next IN ('RUNNING','CANCELLED')) OR
   (old_state='RUNNING' AND p_next IN ('VERIFYING','FAILED','CANCELLED')) OR
   (old_state='VERIFYING' AND p_next IN ('SUCCEEDED','FAILED','CANCELLED'))
 ) THEN RAISE EXCEPTION 'invalid state transition' USING ERRCODE='23514'; END IF;
 IF old_state='APPROVAL_PENDING' AND p_next='RUNNING' AND
    (p_approval IS NULL OR length(trim(p_approval))=0) THEN
    RAISE EXCEPTION 'human approval required' USING ERRCODE='42501';
 END IF;
 UPDATE omega_tasks SET state=p_next,updated_at=now() WHERE task_id=p_task;
 INSERT INTO omega_task_events(task_id,from_state,to_state,approved_by)
 VALUES (p_task,old_state,p_next,CASE WHEN old_state='APPROVAL_PENDING' AND p_next='RUNNING' THEN p_approval ELSE NULL END);
 RETURN p_next;
END; $$;
CREATE OR REPLACE FUNCTION omega_protect_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.state IS DISTINCT FROM OLD.state AND current_setting('omega.transition_authorized',true) IS DISTINCT FROM 'yes'
 THEN RAISE EXCEPTION 'state changes must use omega_transition' USING ERRCODE='42501'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER omega_tasks_guard BEFORE UPDATE OF state ON omega_tasks FOR EACH ROW EXECUTE FUNCTION omega_protect_state();
-- Never grant arbitrary direct DML on this schema to model or agent roles.
