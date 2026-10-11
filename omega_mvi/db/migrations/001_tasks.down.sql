DROP TRIGGER IF EXISTS omega_tasks_guard ON omega_tasks;
DROP FUNCTION IF EXISTS omega_protect_state();
DROP FUNCTION IF EXISTS omega_transition(UUID,TEXT,TEXT);
DROP TABLE IF EXISTS omega_task_events;
DROP TABLE IF EXISTS omega_tasks;
