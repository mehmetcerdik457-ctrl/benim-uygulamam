-- Disposable test DB ONLY, checked by sentinel before any schema changes.
REVOKE ALL ON public.omega_demo_status_counts FROM omega_demo_reader;
DROP VIEW IF EXISTS public.omega_demo_status_counts;
REVOKE USAGE ON SCHEMA public FROM omega_demo_reader;
DROP ROLE IF EXISTS omega_demo_reader;
