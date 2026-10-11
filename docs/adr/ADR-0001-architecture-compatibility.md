# ADR-0001 — Preserve PWA and introduce an isolated OMEGA MVI

**Status: PROPOSED (not owner-approved)**

Context: `AI_MASTER_ROADMAP.md` and `CURRENT_STATE.md` describe an already-accepted PWA runtime, a standard-library Python backend and a hosted provider path; they also mark real provider setup, research, owner cryptography and Android bridge as incomplete. `SECURITY.md` prohibits secrets in source. The 100-step OMEGA v2 specification requires local-first operation, explicit authorization, stateful tasks and source-grounded retrieval.

Decision proposal: do **not** replace or change `backend/server.py`, `start.sh`, the legacy endpoints or PWA acceptance artifacts during Phase 0. Create an opt-in, isolated `omega_mvi/` FastAPI service with its own ports, package, Compose and tests. Start with deterministic mock inference and no external network integration; actual local inference must pass measured owner-hardware tests. Postgres is isolated, non-public and seeded only with dummy data. Never present a hosted provider route as local/private by default.

Alternatives: (A) rewrite legacy backend — rejected for regression risk; (B) reuse hosted API for all prompts — rejected as default due to privacy/local-first objective; (C) separate optional MVI service — preferred pending tests and owner acceptance.

Invariants: prior PWA acceptance records remain historical, not automatically re-tested; `GET /api/health` on old backend remains unchanged; no new provider call, paid service, credential, owner device or public bind by default. Full migration requires separate compatibility ADR, tests and explicit approval.

Acceptance: old regression tests pass on the code branch; dummy-data MVI health endpoint passes locally and under Compose when Docker is available; policy denies unknown actions; docs clearly distinguish runner from owner device. Rollback: delete/revert only the isolated MVI branch/files; leave legacy unchanged.
