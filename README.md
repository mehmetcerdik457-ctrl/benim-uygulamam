# PROJECT OMEGA

PROJECT OMEGA is intended to become a local-first, owner-controlled AI
orchestration platform. The repository is currently a small Python standard
library backend, not the complete platform or the Minimum Viable Inspector.

## Current verified state

- `backend/server.py` serves a small HTTP API. All provider calls are
  **blocked by default** until independent Owner enrollment and policy review;
  `OPENAI_API_KEY` alone never enables provider execution.
- A **separate, synthetic-only** `omega_mvi/` prototype is preserved byte-for-byte
  from PR #58, including FastAPI, PostgreSQL migration tests, task-state policy,
  inspection/retrieval/redaction/PR-review modules and a Turkish demo dashboard.
  Its approval contract and storage exercise disposable fixtures, not real Owner
  enrollment or live task authority. The stdlib backend and FastAPI demo are
  **not** interchangeable or a production-integrated service.
- A real local LLM runtime, real device authorization, full owner-scoped RAG,
  executable task queue and production backup/restore remain unaccepted.
- Provider credentials and external integrations are not provisioned by this
  repository.
- Phase 0 scope and design decisions are documented in
  [`docs/PROJECT_OMEGA_PHASE_0.md`](docs/PROJECT_OMEGA_PHASE_0.md) and
  [`scope.yaml`](scope.yaml).

Do not send confidential data to the existing backend: its configured chat
provider is an external service. No production-readiness claim is made.

## Development

The current backend uses only the Python standard library. Its existing test
suite can be run with:

```sh
python -m pytest
```

See [`SECURITY.md`](SECURITY.md) before reporting security issues.

## Stacked MVI recovery integration

Existing PR #58 MVI code is recovered in `omega_mvi/` with Git blob identifiers
preserved; this is **not** a rewrite and does not use private 0.1.4-dev bytes.
Read `docs/OMEGA_REQUIREMENTS_MATRIX.csv` for historical PR58 statuses (not
acceptance), `compose.omega.yml` for the deliberately isolated demo, and
`.github/workflows/omega-inspector-e2e.yml` for real *disposable* PostgreSQL
and FastAPI HTTP integration checks. All external execution remains denied.
