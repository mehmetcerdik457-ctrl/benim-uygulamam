# MEHMET AI — MASTER ROADMAP

## Current truth
- Canonical PWA runtime acceptance: CLOSED
- Canonical PWA artifact: MEHMET_YARATILIS_PWA_v0.2.2.zip
- Trusted HTTPS / service worker / offline / memory / physical camera / physical microphone / physical TTS / PWA install: PASS
- Real model backend: NOT PROVISIONED
- Web research provider: NOT PROVISIONED
- Owner cryptographic identity: NOT PROVISIONED
- Phone bridge / privileged Android actions: NOT IMPLEMENTED
- Repository visibility: PUBLIC
- Default branch protection: OFF

## Goal
Turn this repository into the central engineering control plane for a secure owner-controlled AI system without mixing product source, secrets, runtime evidence, and experiments.

## Phase 0 — Repository hardening
1. Keep secrets out of Git history. Only placeholders belong in .env.example.
2. Enable branch protection/rulesets for main: PR-only changes, required CI, no force-push, no deletion.
3. Decide whether the repository must remain public. If private product code will live here, move it to a private repository before adding it.
4. Keep CODEOWNERS and SECURITY.md mandatory.
5. Add release tags and immutable evidence for shipped builds.

Acceptance:
- main cannot be changed without required checks.
- secret scanning/privacy guard passes.
- no production secret exists in repository history.

## Phase 1 — Real AI backend
Build a server-side API. Browser/PWA must never contain provider secrets.

Endpoints:
- GET /api/health
- POST /api/chat
- POST /api/research
- GET /api/models

Requirements:
- provider keys server-side only
- request IDs and structured logs
- timeouts/retries
- fail-closed behavior
- provider/model allowlist
- rate limiting
- input/output size limits

Acceptance:
- /api/health = 200
- /api/chat returns a real provider response
- key never appears in browser, source, logs, or network payloads

## Phase 2 — Model router
Add an explicit router for:
- fast/default model
- reasoning model
- coding model
- vision-capable model
- fallback provider

Acceptance:
- deterministic routing rules
- per-request selected model is logged without exposing secrets
- provider failure falls back only according to policy

## Phase 3 — Web research
Implement server-side search/research adapters with:
- citation provenance
- source allow/deny rules
- timeout and result caps
- explicit offline/error state

Acceptance:
- research returns source URLs and timestamps
- no fabricated source on provider failure

## Phase 4 — Owner identity and authorization
Implement owner enrollment and cryptographic authorization:
- Android Keystore-backed owner key
- biometric/device-credential confirmation for high-risk actions
- replay protection
- revocation/recovery
- encrypted owner state

Acceptance:
- non-owner requests rejected
- replayed command rejected
- high-risk command requires fresh authorization

## Phase 5 — Phone bridge
Build the Android bridge separately from the PWA.
Scope:
- observe -> plan -> act -> verify
- Accessibility only where explicitly authorized
- no silent privileged escalation
- postcondition verification
- audit log for every action

Acceptance:
- exact action outcome verified on device
- cancellation/revocation works
- failed action never reported as PASS

## Phase 6 — CI/CD and supply chain
- unit tests
- integration tests
- browser acceptance
- dependency review
- secret/privacy guard
- SBOM
- signed release metadata
- reproducible artifact hashes
- deployment smoke test

Acceptance:
- release is blocked if any required check fails
- release notes include commit SHA, artifact SHA-256 and deployment ID

## Phase 7 — Operations
- health dashboard
- error/latency monitoring
- quota/cost limits
- backup/restore
- incident runbook
- rollback runbook
- Drive evidence snapshot

## Immediate execution order
1. Harden main.
2. Implement real /api/health and /api/chat backend.
3. Add model router.
4. Add web research.
5. Provision owner crypto.
6. Build Android phone bridge.
7. Add signed release pipeline.
8. Run real-device acceptance again only for newly added capabilities.

## Definition of Done
The project is not complete because the PWA shell works. It is complete only when:
- real model backend works,
- research works with provenance,
- owner identity is cryptographically enforced,
- phone actions are authorized and postcondition-verified,
- CI/CD gates releases,
- no secret is exposed,
- recovery and rollback are tested.
