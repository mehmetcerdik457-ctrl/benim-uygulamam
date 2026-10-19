# PROJECT OMEGA

PROJECT OMEGA is intended to become a local-first, owner-controlled AI
orchestration platform. The repository is currently a small Python standard
library backend, not the complete platform or the Minimum Viable Inspector.

## Current verified state

- `backend/server.py` serves a small HTTP API. The provider key is not
  proof of owner identity. Until verified owner authentication is implemented,
  HTTP chat and model-list provider calls are intentionally disabled (403).
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

## Owner identity and execution hold

The owner identity provider, authorization verifier, and review policy are
not implemented. The current `owner_execution_authorized()` gate is always
false and has no environment/header override. Setting `OPENAI_API_KEY` must
not enable external model execution through HTTP endpoints. The health
response reports `execution_enabled=false` until this boundary is satisfied.
Existing offline unit tests may monkeypatch the guard to exercise unrelated
parsers and error paths; such tests do **not** establish real authorization.
Direct Python function calls are not a security isolation boundary; do not
run or expose this backend as a production service.
