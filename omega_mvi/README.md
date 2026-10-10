# PROJECT OMEGA MVI-01 — isolated dummy-only service

**STATUS: EXPERIMENTAL. Not accepted as MVI or Phase 0.** This does not modify the legacy `backend/server.py`, PWA, default run command or `main`.

## Local tests (no API tokens, no service usage)
From repository root, use a virtual environment and:
```sh
python -m pip install -r omega_mvi/requirements-test.txt
python -m pytest -q tests omega_mvi/tests
```
Existing legacy tests must still pass. A normal `pytest -q` with only pytest installed may skip the MVI tests due to optional dependencies; **skips are not acceptance**. The dedicated OMEGA CI job installs explicit test dependencies and checks the MVI tests.

## Isolated Docker demo (explicit opt-in)
1. Install Docker/Compose locally on a device you control. Docker cannot be assumed present in the GitHub runner or on your Android phone.
2. Put a unique, throwaway NON-PRODUCTION demo database password in a private shell environment variable `OMEGA_DEV_DB_PASSWORD`; do not commit it. Never use your real credentials, private data or cloud resources.
3. Run `docker compose -f compose.omega.yml config -q`, then `docker compose -f compose.omega.yml up --build`.
4. In another terminal, check `curl -fsS http://127.0.0.1:18080/health`. The API binds to localhost only; database has no host port. Network between containers is Compose-internal, and DB storage is temporary (`tmpfs`).
5. Stop with `docker compose -f compose.omega.yml down`. No production resource should be involved.

The app intentionally reports `production_ready=false`, `mode=mock`, `owner_hardware=UNKNOWN`; `POST /api/execute` and `POST /api/chat` return HTTP 403. PostgreSQL is present as a demo health-checked container; **there is no database schema or migration yet** (MVI-02). Future production setup must remove all demo assumptions and add authentication, a real policy engine, migration, key management and release hardening.

Rollback: revert this draft branch or remove `compose.omega.yml` and `omega_mvi/` without touching existing app data. Do not merge/deploy until explicit human approval and independently verified tests.
