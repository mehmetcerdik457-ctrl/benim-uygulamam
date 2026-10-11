# MVI-03: explicit owner-approval test contract — NOT enabled

Branch is stacked on draft PR #28 and tracks Issue #29. Files under `approval/` are offline-only contract and synthetic unit tests; no real IdP, authenticated user session, hardware identity, or production database grants are available.

An approval MUST bind immutable task ID, verified actor, action, resource and scope, expiration, one-time ID and issuer. Test ledger uses only a process Lock and is NOT SQL durable. `require_live_verified_owner()` always raises `ApprovalUnavailable`, even with a plausible signed-looking object. Model text cannot grant approval.

NEXT BLOCKED: independently verify a real identity provider, create a PostgreSQL ledger owned by a non-login migration role, use a trusted atomic SQL verification/consume routine with expiring approvals, test concurrency/replay and ownership with a restricted runtime role, require operator approval and audit. Before these proofs the original SQL `APPROVAL_PENDING → RUNNING` gate must stay closed.
