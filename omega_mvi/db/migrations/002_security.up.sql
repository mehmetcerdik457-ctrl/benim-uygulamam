-- P0 security hardening. Transactionally applied only to isolated sentinel-verified demo DB.
-- omega_demo is a disposable CI bootstrap superuser; NEVER reuse these role names
-- or credentials in a real environment. Real identity verification is NOT provisioned.
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'omega_demo_migrator') THEN
   CREATE ROLE omega_demo_migrator NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'omega_demo_runtime') THEN
   CREATE ROLE omega_demo_runtime NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;
 END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON omega_tasks, omega_task_events FROM PUBLIC;
REVOKE ALL ON omega_tasks, omega_task_events FROM omega_demo_runtime;
REVOKE EXECUTE ON FUNCTION omega_transition(UUID,TEXT,TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION omega_protect_state() FROM PUBLIC;

-- Even arbitrary nonempty approval text never authorizes RUNNING.
-- With no trusted owner authentication, execution is intentionally unavailable.
CREATE OR REPLACE FUNCTION omega_transition(p_task UUID,p_next TEXT,p_approval TEXT DEFAULT NULL)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE old_state TEXT;
BEGIN
 SELECT state INTO old_state FROM public.omega_tasks WHERE task_id=p_task FOR UPDATE;
 IF old_state IS NULL THEN RAISE EXCEPTION 'task not found' USING ERRCODE='P0002'; END IF;
 IF old_state='APPROVAL_PENDING' AND p_next='RUNNING' THEN
   RAISE EXCEPTION 'verified human identity and approval service unavailable' USING ERRCODE='42501';
 END IF;
 IF NOT (
   (old_state='CREATED' AND p_next IN ('PLANNED','CANCELLED')) OR
   (old_state='PLANNED' AND p_next IN ('APPROVAL_PENDING','CANCELLED')) OR
   (old_state='APPROVAL_PENDING' AND p_next='CANCELLED') OR
   (old_state='RUNNING' AND p_next IN ('VERIFYING','FAILED','CANCELLED')) OR
   (old_state='VERIFYING' AND p_next IN ('SUCCEEDED','FAILED','CANCELLED'))
 ) THEN RAISE EXCEPTION 'invalid state transition' USING ERRCODE='23514'; END IF;
 UPDATE public.omega_tasks SET state=p_next,updated_at=pg_catalog.now() WHERE task_id=p_task;
 INSERT INTO public.omega_task_events(task_id,from_state,to_state,approved_by)
 VALUES (p_task,old_state,p_next,NULL);
 RETURN p_next;
END;
$function$;
-- Trigger checks the executing ROLE, not an attacker-controlled session GUC.
CREATE OR REPLACE FUNCTION omega_protect_state() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $function$
BEGIN
 IF NEW.state IS DISTINCT FROM OLD.state AND current_user <> 'omega_demo_migrator'
 THEN RAISE EXCEPTION 'state changes require privileged transition routine' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END;
$function$;
CREATE FUNCTION omega_guard_events() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $function$
BEGIN
 RAISE EXCEPTION 'audit records are immutable' USING ERRCODE='42501';
END;
$function$;
CREATE TRIGGER omega_events_immutable BEFORE UPDATE OR DELETE ON omega_task_events
FOR EACH ROW EXECUTE FUNCTION omega_guard_events();

-- Separate ownership from runtime. Migrator has NOLOGIN and runtime has no membership.
ALTER TABLE omega_tasks OWNER TO omega_demo_migrator;
ALTER TABLE omega_task_events OWNER TO omega_demo_migrator;
ALTER FUNCTION omega_transition(UUID,TEXT,TEXT) OWNER TO omega_demo_migrator;
ALTER FUNCTION omega_protect_state() OWNER TO omega_demo_migrator;
ALTER FUNCTION omega_guard_events() OWNER TO omega_demo_migrator;

-- PostgreSQL grants function EXECUTE to PUBLIC by default; revoke atomically.
REVOKE ALL ON FUNCTION omega_transition(UUID,TEXT,TEXT) FROM PUBLIC, omega_demo_runtime;
REVOKE ALL ON FUNCTION omega_protect_state() FROM PUBLIC, omega_demo_runtime;
REVOKE ALL ON FUNCTION omega_guard_events() FROM PUBLIC, omega_demo_runtime;
GRANT USAGE ON SCHEMA public TO omega_demo_runtime;
-- Deliberately NO SELECT/INSERT/UPDATE/DELETE/EXECUTE/CREATE grants to runtime
-- until authenticated identity and owner authorization exist (MVI-03).
