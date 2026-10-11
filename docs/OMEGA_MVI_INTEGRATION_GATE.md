# PROJECT OMEGA V2.0 — MVI integration gate

This branch is an integration staging area, not an accepted or deployed MVI.
The original 100-item master specification is authoritative. No status becomes DONE without successful tests, independent review and owner acceptance.

## Dependency order (do not cherry-pick blindly)
1. PR #19 master spec / scope, then PR #22 matrix and contract checks (resolve PR #21 scope conflict with PR #34; no access expansion).
2. PR #24 MVI-01 Compose/FastAPI baseline.
3. PR #28 MVI-02 PostgreSQL schema and integration tests, including security migration.
4. PR #35 MVI-03 synthetic approval contract: keep runtime execution denied without authenticated owner proof.
5. PR #33 model adapter (fake only); PR #37 localhost/legacy regression tests.
6. PR #40 local CI/Privacy Guard; already staged on this branch.

## Hard acceptance gates
- Preserve original app/backend and main; no merge or deploy without explicit owner approval.
- Run all tests together on the exact integration head SHA with disposable PostgreSQL; check migration up/down, table safety, ownership, permissions, budget, deadline and approval fail-closed.
- Verify PR #38/#39 target branches independently; a merge into a feature branch is not a main merge.
- Keep the 100-row requirements matrix evidence-based; this staging branch does not assert completion.
- Verify no secret value is logged or indexed; no access to additional repositories or cloud accounts.

## Current limits
This is a dependency manifest and CI staging baseline only. Other PR contents are NOT yet integrated. No integration test result or owner acceptance is claimed.
