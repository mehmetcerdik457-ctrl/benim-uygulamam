-- ONLY the sentinel-verified CI fixture may invoke DOWN.
ALTER TABLE public.omega_tasks
 DROP CONSTRAINT IF EXISTS omega_deadline_valid,
 DROP CONSTRAINT IF EXISTS omega_permissions_readonly,
 DROP CONSTRAINT IF EXISTS omega_currency_supported,
 DROP CONSTRAINT IF EXISTS omega_budget_nonnegative,
 DROP COLUMN IF EXISTS deadline_utc,
 DROP COLUMN IF EXISTS permissions,
 DROP COLUMN IF EXISTS budget_currency,
 DROP COLUMN IF EXISTS budget_limit_minor;
