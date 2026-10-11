# MVI-02 — isolated, reversible PostgreSQL prototype

This is a test-only, non-production schema and is NOT a secure production authorization layer. Requires a real PostgreSQL endpoint; never use a user account DB or a real secret. No project data or sensitive values are stored by test fixtures.

Run the GitHub workflow `OMEGA MVI-02 real PostgreSQL integration`: a random throwaway password is generated in the runner and is never committed; Postgres uses tmpfs storage and no host-published port; the integration-test image joins only the `internal: true` Docker network.

Migration CLI: `python -m db.migrate up` / `python -m db.migrate down` from an isolated container with `OMEGA_DATABASE_URL` provided at runtime; no connection-string logging. Transaction plus PostgreSQL advisory lock, schema version table, repeat-up/down idempotence. Down destroys the disposable task tables and all their data; NEVER run against non-demo DBs.

The task store accepts a limited allowlist of metadata keys; no tokens, raw prompts or private inventory belong in it. State transitions are restricted by database function and a guard trigger; the `APPROVAL_PENDING → RUNNING` check in this prototype requires a nonempty approval reference. This **does not verify human identity**; MVI-03 must introduce separate authenticated approval records and narrow DB grants before any real agent task execution. The normal `omega_mvi/app/main.py` refuses execution/chat. A distinct, test-only FastAPI factory is used in integration tests for real SQL-backed create/read.

Rollback: revert the draft MVI-02 branch; test-run database uses tmpfs and is deleted on Compose down. For future real databases, backup/restore, migration upgrades and rollback need separately reviewed approval.
