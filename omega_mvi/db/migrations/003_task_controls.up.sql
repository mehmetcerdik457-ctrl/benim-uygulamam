-- OMEGA-053: safe, declarative task constraints. No execution authorization.
ALTER TABLE public.omega_tasks
 ADD COLUMN budget_limit_minor BIGINT NOT NULL DEFAULT 0,
 ADD COLUMN budget_currency TEXT NOT NULL DEFAULT 'USD',
 ADD COLUMN permissions TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 ADD COLUMN deadline_utc TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '1 hour');
ALTER TABLE public.omega_tasks
 ADD CONSTRAINT omega_budget_nonnegative CHECK (budget_limit_minor BETWEEN 0 AND 1000000000),
 ADD CONSTRAINT omega_currency_supported CHECK (budget_currency IN ('USD','TRY')),
 ADD CONSTRAINT omega_permissions_readonly CHECK (
  permissions <@ ARRAY['repository:read','inventory:read','rag:read','pr:read']::TEXT[]
  AND array_position(permissions,NULL) IS NULL
 ),
 ADD CONSTRAINT omega_deadline_valid CHECK (
  deadline_utc > created_at
  AND deadline_utc <= created_at + INTERVAL '365 days'
 );
-- No runtime privilege GRANT. Budget is inert and cannot cause spending.
