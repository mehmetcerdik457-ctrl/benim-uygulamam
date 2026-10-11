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
