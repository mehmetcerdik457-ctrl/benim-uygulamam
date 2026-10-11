# PROJECT OMEGA

PROJECT OMEGA is intended to become a local-first, owner-controlled AI
orchestration platform. The repository is currently a small Python standard
library backend, not the complete platform or the Minimum Viable Inspector.

## Current verified state

- `backend/server.py` serves a small HTTP API and can call OpenAI when
  `OPENAI_API_KEY` is configured.
- No local model runtime, database, task queue, inventory, RAG, web interface,
  or approval workflow is implemented.
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
