# PROJECT OMEGA — Specialist 3 / Architecture, Inventory, Provenance

**Audit date:** 2026-10-11. **Disposition:** DRAFT / NOT ACCEPTED. No production, merge, deployment, real filesystem scan, backup, real secret or private Drive content access.

## Authoritative source separation

- Public `main` at `4c53df868a028e51c546d0eefe1d9d45c063c645`.
- Stacked draft PR #58 at initial audited head `044c558b2b28e05929a9acd79a639a32092ab187`. Neither is evidence of production readiness.
- Owner-private local `0.1.4-dev` at `053e75d5591c836714d27d2d8b9b3f74c4464b9f`: **NOT ACCESSED / NOT COMPARED / NOT TESTED**. No assumption of identical sources.
- Canonical text: [OMEGA V2 master specification](https://docs.google.com/document/d/1TBRiXs9sf6Cdz3IVMQa5-zTLn-cRu0Rn-6EAdQHFoNM/edit), backed by `docs/PROJECT_OMEGA_MASTER_SPEC_V2.md`; central coordination [Issue #25](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/issues/25).

## Inventory of actual GitHub trees (OMEGA-001)

Machine-readable list of **every Git tree blob path, Git object SHA-1, mode, size and category** for each observed ref: `docs/evidence/OMEGA_PUBLIC_GITHUB_TREE_INVENTORY_20261011.json`. Listing is exhaustive according to non-truncated recursive Git tree results **at those refs**, not a claim that every file's contents or Git history was independently audited.

| Snapshot | Files | Directories | CI workflow files | OMEGA MVI files | Root tests | Tracked LICENSE |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| main `4c53df8` | 21 | 6 | 3 | 0 | 2 | ABSENT |
| PR #58 `044c558` | 107 | 20 | 10 | 53 | 12 | ABSENT |

Reading completed for: master specification, `AGENTS.md`, `README.md`, `AI_MASTER_ROADMAP.md`, `CURRENT_STATE.md`, `SECURITY.md`, `scope.yaml`, CI workflow, architecture and existing ADRs, discovery proposal PR #21, Phase-0 acceptance, GitHub inventory module/tests, inspection pipeline, database security SQL, requirements matrix and PR #58/Issue #25 metadata. **Other paths were enumerated by Git tree, not all content-reviewed.** `.env.example` contents and actual secret values deliberately NOT inspected. Git blob SHA-1 does **not** equal a file-content SHA-256. No license document in either tree means license status is **unresolved**, not that reuse is unrestricted. Existing PWA acceptance assertions remain historical and were not independently retested.

## Requirement-specific old/new status and gates

| Requirement | Old state at PR #58 baseline | New isolated work (proposal, no acceptance) | Remaining blocker |
| --- | --- | --- | --- |
| #1 Repo inventory | PARTIAL; prior discovery at PR #21 sampled 18 paths and `main` had evolved | Full tree-path/size/Git-object manifest on `main` and PR #58; license absence noted | Owner/license decision, full content/security/history audit, reviewer verification |
| #5 ADR decisions | PARTIAL; ADR-0001/0002 and recovery sketch, backup encryption selection unresolved | `ADR-0003-client-side-backup-encryption.md` alternatives, client-side crypto/recovery gates | Owner decision, custody design review, fixture restore/corruption tests |
| #14 Safe disk scan | NOT_STARTED / post-MVI; scope explicitly denies local device | Read-only acquisition and custody SOP, strong default-deny; **no live scanner** | Signed scope service, owner RO mount/forensic consent and real-device negative tests |
| #19 SHA-256 versioned index | NOT_STARTED / post-MVI | Synthetic fixture index with independent content and metadata hashes, version chain and tamper rejection | Approved live acquisition, ACL/xattr OS mapping, independent end-to-end verification |
| #20 Provenance | NOT_STARTED / P1; depends on #17 | Synthetic source/version, owner-ref, access level, UTC verification, retention and hashes; drift tests | Authorized persistent provenance table, identity/ACL, signed append-only custody log, retention enforcement |

## Local synthetic test observation

Command: `PYTHONPATH=. python -m pytest -q omega_mvi/inspection/provenance/test_index.py` against isolated copied code and no owner data. **13 PASS / 0 FAIL / 0 SKIP (exit 0)**. GitHub CI on the newly proposed PR must independently run and be inspected at its **exact final SHA** before citing CI acceptance. Tests do not exercise database, signed manifests, real ACLs, actual filesystem traversal, atime, Docker, PR #58 host-loopback or private `0.1.4-dev`.

## Files confined to this specialist

1. `omega_mvi/inspection/provenance/__init__.py` — new offline synthetic-only contract, without touching existing GitHub inventory, task, retrieval, redaction or API modules.
2. `omega_mvi/inspection/provenance/test_index.py` — source/path denied, content/metadata/provenance changes and version tamper tests.
3. `docs/adr/ADR-0003-client-side-backup-encryption.md` — proposed choices and owner gates.
4. `docs/OMEGA_LOCAL_READONLY_EVIDENCE_PROCEDURE.md` — safe scope, disk evidence chain, integration contract.
5. `docs/evidence/OMEGA_PUBLIC_GITHUB_TREE_INVENTORY_20261011.json` — public Git tree manifest.
6. This report.

## Integrator handoff (NOT performed)

The integration owner should own **all changes to shared** `scope.yaml`, root CI, `compose.omega.yml`, `omega_mvi/db/migrations`, API endpoints and 100-row matrix. Specifically plan a provenance table with scoped `source_ref`, owner/ACL/verification/retention, signed chain-of-custody ledger, least-privilege RLS and synthetic rollback tests; keep live-device scan denied until an externally verified owner approval exists. Do not change #14/#19/#20 statuses to DONE or claim Phase 0 signoff from this PR.

## Security / rollback

No existing sources deleted; no main branch writes, permission changes, paid services, deployments, merging or backup upload. Revert/close only this stacked draft PR to roll back the proposal. Never publish owner-private path-level evidence, actual file hashes, secret data or recovery information in public Issue #25.

---

## Follow-up: adverse provenance tests and corrective audit (2026-10-11)

### Evidence chain preserved — including initial failure

- Original draft head: `d65423521168a94006f07145d8d420d40e4fd4cd`; six workflows SUCCESS, CI 123 PASS / 18 SKIP. This remains historical evidence, **not the current head**.
- First new strict-validation attempt: `2c71e492120b32fd51ad4be891f271904f4de635`, [CI run 38159098827](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159098827), **FAIL: 5 failed / 146 passed / 18 skipped**. Negative tests exposed acceptance of `.` and `..` path segments. It was **not** an accepted revision.
- Corrective code commit: `2f480886a0f097362282499afbc67ad00214893c`, [CI run 38159182606](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182606) **SUCCESS: 151 passed / 18 skipped / 1 warning**. Relative-path segments `.` and `..` are now denied for both record creation and independently supplied records. The extra negative tests increased the fixture test count from 13 to **41**.
- At that **exact corrective code SHA**, GitHub workflow outcomes were **six SUCCESS**: [CI](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182606), [Privacy Guard](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182617), [isolated MVI](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182599), [PostgreSQL](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182575), [integrated MVI](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182547), [E2E](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38159182568). E2E reported **36 DB, 4 HTTP, 106 regression PASS**. **Runner-host remains BLOCKED_NOT_ACCEPTED** with MISSING host binding, REFUSED TCP and BLOCKED HTTP. Workflows succeeding does **not** close the separate host-acceptance gate.
- This appended documentation requires a new commit; CI must also be rechecked at that **new** head before anyone cites branch-wide status as final.

### Hardening scope and limits (OMEGA-014/019/020)

The offline provenance constructor and validator now both enforce a bounded allowlisted `synthetic://` source, ASCII-only safe fixture components, opaque `owner:` reference, required timestamp with timezone and UTC normalization, positive bounded retention days, strict record/index field sets, and genesis `version=1` plus consecutive hash-linked versions. Explicitly reject missing/unknown ACL and xattr hashes: a verified digest is mandatory even for a synthetic empty metadata representation; **never silently substitute a zero or empty hash for an unreadable real ACL**. SHA-256 records are not digitally signed; an adversary able to rewrite the entire archive may recompute all hashes. A trusted separately stored signed anchor and independent ownership/custody verification remain required.

The module stays I/O-free and never grants permission to read a local disk; it processes only caller-provided tiny disposable byte fixtures. These synthetic tests do not establish absence of race conditions, atime changes, NTFS/Windows semantics, long-path normalization, ACL collection correctness, actual retention deletion or owner approval.

### Additional critical source-code reading (OMEGA-001)

A second bounded GitHub read fetched full UTF-8 file bodies at PR #58 base `044c558b2b28e05929a9acd79a639a32092ab187` for these **ten** previously under-reviewed high-impact paths: `backend/server.py`, `omega_mvi/app/main.py`, `omega_mvi/db/store.py`, `omega_mvi/db/migrate.py`, `omega_mvi/approval/contract.py`, `omega_mvi/inspection/retrieval/__init__.py`, `omega_mvi/inspection/redaction/__init__.py`, `omega_mvi/inspection/pr_review/engine.py`, `omega_mvi/requirements.txt` and `compose.omega.yml`. Function/declaration and endpoint signals were extracted without publishing credential values or raw bodies.

Observed boundaries: the legacy backend has an explicit hosted OpenAI endpoint and cannot be labeled a local model; new FastAPI has `/health`, `/api/readiness` and demo-only endpoints; SQL migrations and the proposal-level approval layer exist but are **not** evidence of a signed owner production identity. The original 107-path Git tree inventory is exhaustive **only at the tracked-path level**, and this added sampling is **not full line-by-line security review of all 107 blobs**, repository history, dependencies, licenses or owner device. License file absence remains unresolved.

### Constrained proposed persistence contract for integration owner only (OMEGA-020)

Do **not** apply a database migration from this specialist branch. Proposed future private `omega_provenance` schema must bind, at minimum: `source_ref` + scoped immutable source ID, privately encrypted normalized path alias and source version, `owner_ref`, effective ACL/access level and classification, UTC collection/last-verification instant, explicit retention policy and expiry/hold state, content SHA-256, canonical metadata SHA-256 and append-only record digest/version. Reject missing provenance or unverified ACL; do not rely on free-form task metadata. Enforce tenant/owner isolation and least-privilege RLS in real PostgreSQL, plus unique source/path/version identity, deny direct mutation of custody events, append-only signed chain with independently verified trust anchors, and separate retention/deletion/revocation gates. Run synthetic migration/rollback/replay/cross-owner/clock-skew tests in a disposable DB before any private owner source is allowed.

**Acceptance stays OPEN:** OMEGA-001 PARTIAL, -005 PARTIAL, -014 BLOCKED, -019 PARTIAL, -020 PARTIAL. No `scope.yaml`, Compose, shared CI, migration or app changes from this specialist. Final integration and owner authorization belong to the coordinator.


## Third audit pass — 2026-10-12 (provenance chain and access drift)

**Source boundary unchanged:** public PR #58 baseline `044c558b2b28e05929a9acd79a639a32092ab187`, separate PR #61 branch, no merge, and private local `0.1.4-dev` (`053e75d5591c836714d27d2d8b9b3f74c4464b9f`) **not inspected**.

### New isolated implementation

- `omega_mvi/inspection/provenance/__init__.py`: `verify_index_chain()` checks up to 128 snapshots, strict genesis/version/order/previous-hash links and independently provided genesis/tip SHA-256 checkpoints; **a checkpoint from the same untrusted chain is NOT an authentication source**.
- `omega_mvi/inspection/provenance/test_index.py`: extra synthetic replay/truncation/recompute/anchor tests; previous first hardened CI [38224920857](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38224920857) at code HEAD `85ef6bced20dd8c0d052b52c7539935a68cad19b` reported **165 passed, 18 skipped**. This is historical commit evidence, not evidence of all subsequently added modules.
- **New** `omega_mvi/inspection/provenance/policy.py` and `test_policy.py`: report synthetic source additions/deletions and version/owner/access classification/retention-policy changes as requiring external review; recognize POSIX mode, UID, GID, ACL and xattr digest changes as permission-sensitive even when `access_level` text stays constant. Distinguish mtime-only changes from permission drift. The report **never grants** approval, identity verification, deletion or retention-enforcement authority.
- `docs/OMEGA_LOCAL_READONLY_EVIDENCE_PROCEDURE.md`: explicit independent anchor and retention lifecycle restrictions. `verified_at` is NOT trusted original acquisition time, and `retention_days` cannot prove policy expiry without an separately anchored collection event.

### Additional bounded full-text reads for OMEGA-001

At PR #58 exact baseline SHA, 20 further previously under-reviewed public document/source/test file bodies were fetched as text and path-specific Git blob identifiers read back: ten scope, runner host, model, MVI, database/approval documentation and UI interface files; plus ten runner/secret guard, rollback migration, DB test and task-policy source files. These reads establish **availability/content inspection at a fixed public commit**, not complete semantic security coverage. The 107 tracked Git-tree blobs remain inventoried by path/mode/size/Git SHA-1 from the initial report. Environment template contents were deliberately excluded from bulk reading. The whole repository, past Git history, licensing of future artifacts and owner-private files remain **NOT FULLY AUDITED**.

### Persistent acceptance and integration limits

OMEGA-001 PARTIAL (tracked paths complete at two refs; security/license audit open). OMEGA-005 PARTIAL (encrypted backup ADR proposed only). OMEGA-014 BLOCKED (owner file roots/RO mount not authorized). OMEGA-019 PARTIAL (synthetic anchored history only; no signed trusted checkpoint). OMEGA-020 PARTIAL (synthetic authority-independent drift report; no PostgreSQL custody table, no signed events, no expiration/deletion evidence). Require a separate real identity and independently signed actor/resource/scope decision to authorize live operations. No code in this specialist branch accesses owner hardware, private source, backups, cloud accounts, secrets or money.

**Exact-head CI note:** Actions on the final updated documentation commit must be fetched and reported separately; prior success cannot be copied forward. A queued or skipped job is NOT a PASS.
