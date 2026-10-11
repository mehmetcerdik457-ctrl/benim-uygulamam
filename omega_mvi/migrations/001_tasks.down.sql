-- Explicit destructive rollback, permitted ONLY in disposable test DB.
DROP TRIGGER IF EXISTS omega_tasks_guard ON omega_tasks;
DROP FUNCTION IF EXISTS omega_guard_task_update();
DROP TABLE IF EXISTS omega_demo_approvals;
DROP TABLE IF EXISTS omega_tasks;
