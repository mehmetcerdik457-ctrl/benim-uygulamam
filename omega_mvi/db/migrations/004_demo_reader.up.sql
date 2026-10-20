-- Demo-only aggregate over real PostgreSQL task records; no raw task exposure.
-- Applied only after independent CI sentinel check. Never use real user data.
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='omega_demo_reader') THEN
   CREATE ROLE omega_demo_reader LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
 END IF;
END $$;
-- View has only two non-identifying columns, owner/data/IDs never exposed.
CREATE VIEW public.omega_demo_status_counts WITH (security_barrier=true) AS
 SELECT state, COUNT(*)::BIGINT AS count FROM public.omega_tasks GROUP BY state;
ALTER VIEW public.omega_demo_status_counts OWNER TO omega_demo_migrator;
REVOKE ALL ON public.omega_demo_status_counts FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO omega_demo_reader;
GRANT SELECT ON public.omega_demo_status_counts TO omega_demo_reader;
REVOKE ALL ON public.omega_tasks,public.omega_task_events FROM omega_demo_reader;
REVOKE EXECUTE ON FUNCTION public.omega_transition(UUID,TEXT,TEXT) FROM omega_demo_reader;
