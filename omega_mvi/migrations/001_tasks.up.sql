-- OMEGA MVI-02: all data is synthetic; no privileged roles or real owner data.
CREATE TABLE omega_tasks (
  task_id UUID PRIMARY KEY,
  owner TEXT NOT NULL CHECK (owner ~ '^demo-[a-z0-9_-]{1,40}$'),
  state TEXT NOT NULL DEFAULT 'CREATED' CHECK (state IN (
    'CREATED','PLANNED','APPROVAL_PENDING','RUNNING',
    'VERIFYING','SUCCEEDED','FAILED','CANCELLED'
  )),
  trace_id TEXT NOT NULL CHECK (trace_id ~ '^demo-[a-z0-9_-]{1,64}$'),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(metadata) = 'object'
      AND (metadata - 'label' - 'category' - 'priority') = '{}'::jsonb
      AND octet_length(metadata::text) <= 1024),
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (owner, trace_id)
);
CREATE INDEX omega_tasks_owner_created_idx ON omega_tasks(owner, created_at DESC);

-- This is a TEST-ONLY approval record. It is NOT a production identity proof.
CREATE TABLE omega_demo_approvals (
  task_id UUID PRIMARY KEY REFERENCES omega_tasks(task_id) ON DELETE CASCADE,
  reviewer TEXT NOT NULL CHECK (reviewer ~ '^demo-reviewer-[a-z0-9_-]{1,30}$'),
  approved_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION omega_guard_task_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.task_id IS DISTINCT FROM OLD.task_id OR
     NEW.owner IS DISTINCT FROM OLD.owner OR
     NEW.trace_id IS DISTINCT FROM OLD.trace_id OR
     NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'immutable task identity' USING ERRCODE = '23514';
  END IF;
  IF NEW.state IS DISTINCT FROM OLD.state THEN
    IF NOT (
      (OLD.state = 'CREATED' AND NEW.state IN ('PLANNED','CANCELLED')) OR
      (OLD.state = 'PLANNED' AND NEW.state IN ('APPROVAL_PENDING','CANCELLED')) OR
      (OLD.state = 'APPROVAL_PENDING' AND NEW.state IN ('RUNNING','CANCELLED')) OR
      (OLD.state = 'RUNNING' AND NEW.state IN ('VERIFYING','FAILED','CANCELLED')) OR
      (OLD.state = 'VERIFYING' AND NEW.state IN ('SUCCEEDED','FAILED'))
    ) THEN
      RAISE EXCEPTION 'invalid state transition' USING ERRCODE = '23514';
    END IF;
    IF OLD.state = 'APPROVAL_PENDING' AND NEW.state = 'RUNNING'
       AND NOT EXISTS (SELECT 1 FROM omega_demo_approvals a WHERE a.task_id = OLD.task_id)
    THEN
      RAISE EXCEPTION 'approval required' USING ERRCODE = '23514';
    END IF;
  END IF;
  NEW.updated_at = clock_timestamp();
  RETURN NEW;
END;
$$;
CREATE TRIGGER omega_tasks_guard BEFORE UPDATE ON omega_tasks
  FOR EACH ROW EXECUTE FUNCTION omega_guard_task_update();
