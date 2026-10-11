-- Only executed after disposable DB URL + independent nonce verification.
-- Reversal immediately precedes migration 001 DOWN in the SAME transaction.
DROP TRIGGER IF EXISTS omega_events_immutable ON omega_task_events;
DROP FUNCTION IF EXISTS omega_guard_events();
REVOKE USAGE ON SCHEMA public FROM omega_demo_runtime;
ALTER TABLE omega_tasks OWNER TO omega_demo;
ALTER TABLE omega_task_events OWNER TO omega_demo;
ALTER FUNCTION omega_transition(UUID,TEXT,TEXT) OWNER TO omega_demo;
ALTER FUNCTION omega_protect_state() OWNER TO omega_demo;
DROP ROLE IF EXISTS omega_demo_runtime;
DROP ROLE IF EXISTS omega_demo_migrator;
