# PROJECT OMEGA — Operations and recovery evidence (OMEGA-090/092/093/094/097/099)

**Scope:** PUBLIC GitHub integration candidate only; base PR #58 HEAD at branch creation `044c558b2b28e05929a9acd79a639a32092ab187`. This document is not an attestation about owner-private local 0.1.2, 0.1.3, 0.1.4/0.1.4-dev or encrypted Drive backups. Main and PR draft revisions must never be called the same deployment.

**Production acceptance:** DENIED until owner/independent reviewer approve exact release SHA, rollback, actual authorization, complete restore, real telemetry, verified dependencies and operational safeguards. All processes default to read-only / dry-run. This PR introduces no production configuration, accounts, secret, deployment, or permission expansion.

## Auditable status (update from exact-SHA CI, never from a previous run)

| Requirement | Evidence in this candidate | Missing gate |
| --- | --- | --- |
| OMEGA-090 freeze + rollback | No deployed freeze switch or rollback reconciler. This runbook defines a human decision gate; versioned DB up/down in isolated CI is **not** production code rollback. | Automated, authorized freeze, last-known-good SHA artifacts, regression diff and rollback rehearsal |
| OMEGA-092 real Grafana telemetry | No Grafana datasource/panel or authenticated error, latency, queue, model and resource telemetry in this inspected tree. | Owner-approved metrics endpoint, least-privilege collection, dashboards, redaction, retention and fault-injection test |
| OMEGA-093 backup/restore | `scripts/omega_ops_isolated_restore.sh` and `omega-ops-recovery.yml` attempt disposable PostgreSQL v4 migrations, wrong marker denial, a custom-format **synthetic fixture only** dump and restoration in a second throwaway database, down/up verification. A green CI run is required before PASS. | Real permitted restore rehearsal with independently protected key material, encryption, RPO/RTO, time-to-recover, owner host verification. Never replay onto existing databases |
| OMEGA-094 SBOM/supply chain | `omega_ops_source_inventory.py` counts direct pinning, Docker base-image digest pins and Action SHA references; returns truthful NOTRUN for full SBOM / image vulnerability scan. | Complete resolved dependency SBOM with hashes and license data, image digests and real CVE/policy scan with retained evidence; disk shortage => NOTRUN, no disk purchase |
| OMEGA-097 emergency stop & revocation | Mock API currently rejects `/api/execute` and `/api/chat`; this is **not** a distributed kill switch, incident alert or verified revocation. | Authenticated, persistent, fail-closed distributed emergency halt, evidence of in-flight cancellation, token/key revocation and tamper-evident incident records |
| OMEGA-099 documentation | This is a non-production operator runbook; existing demo readmes and API remain narrower than required. | User/ops/API/install/recovery docs verified with a non-technical owner on supported hardware |

## Non-destructive release freeze / rollback decision procedure (090)

1. If security/privacy check fails, version or SHA mismatches, database verification fails, an operational alert fires, or a user reports unexpected execution: **FROZEN**. Stop promotions, auto-merge, deployment and new authorized execution through actual privileged controls; do not rely on an assistant's chat text as enforcement.
2. Record suspected incident timestamp (UTC), affected environment identity and exact deployed SHA, independent reviewer, checks per SHA, component versions, and affected assets. Record only non-secret IDs. Never record credentials, private inventories or key-recovery text.
3. Compare the candidate exact SHA and last known independently approved SHA using the *same* relevant tests, security gates, migration compatibility and sanitized metrics. Treat unrun/missing tests as failures to accept. Distinguish CI runner, Docker-internal and owner-host observations.
4. If owner-authorized rollback is needed, take an approved encrypted backup and validate its private manifest **before** acting. Decide on code-only or schema rollback; do not run `db.migrate down` outside sentinel-approved disposable CI. For actual production formulate a separately authorized reversible plan with data-loss and migration compatibility analysis.
5. Keep the release frozen until verified owner and independent reviewer confirm restoration, genuine service denial where required, reconciliation and post-incident regression tests. The existing system does **not** provide these controls as an enforceable automated pipeline.

## Grafana / operational metric contract (092)

Minimum evidence, absent here: request error ratio and latency histogram, task queue ready/running/retry/failed and age gauges, model error/latency/cost histograms by safe coarse category, CPU/RAM/GPU/VRAM and disk resource gauges, ingestion timestamp, true source identity and staleness/denial indicators. No owner IDs, tokens, trace payloads, task prompts or high-cardinality private labels. Validate by synthetic injected failure/slow request/queue backlog and compare measured series to ground truth; inspect datasource ACL, TLS, retention, metrics-export permissions, alert silence and no-data behavior. Static dashboard screenshot is NOT telemetry acceptance.

## Sentinel-guarded synthetic restore (093)

Only GitHub-hosted runner in this exact repository, numeric run ID, random CI-generated marker and password, unique Compose project `omega-ops-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`; verify DB tmpfs, internal Docker network, no DB host published ports and no persistent DB volumes. New CI database `omega_demo`, second scratch restore DB `omega_ops_restore`. Run negative marker denial; run migrations 001–004 UP; create two fixed non-sensitive fixture rows; `pg_dump -Fc` only that fixture table; `pg_restore --no-owner --no-privileges` into empty scratch DB; compare deterministic aggregate digests; DOWN, inspect versions and table absence; UP again. Dumps stay only in disposable DB container, no Actions artifact. Scoped Compose project is cleaned on exit, including error paths. Any failed or skipped check means NOT_ACCEPTED.

**Do not run this CI script on private servers.** Never connect to, delete, down-migrate, restore into, or recreate live PostgreSQL/Qdrant volumes. Do not modify 0.1.2, 0.1.3, 0.1.4 or encrypted backups. No claim their checksums were read or verified.

## Dependency/supply chain acceptance (094)

Source pins are only a partial supply-chain guard; `python:3.12-slim` and `postgres:16-alpine` currently are **tag-based**, not immutable digest locks. Use immutable digests only after independently inspecting images. `omega_ops_source_inventory.py` intentionally does **not** label its inventory as a full transitive SBOM or vulnerability assessment. A future admissible build requires resolved Python packages plus transitive licenses/hashes, OCI digests, genuine pinned GitHub Actions, SBOM provenance tied to image digest, vulnerability scanner invocation, report retention and blocking threshold policy. If runner disk is inadequate, report `NOTRUN: insufficient disk` and DO NOT expand capacity or buy storage without authorization.

## Incident / emergency stop and access-revocation procedure (097)

1. Declare incident with synthetic/non-secret incident ID, time, affected exact SHA and severity. Freeze releases and prevent new task admissions using an independently confirmed enforcement point. Test the denial; mock `403` alone is not proof for actual production agents.
2. Have the authorized owner revoke scoped compromised credentials at the provider/IdP and check expiry/reuse/remaining session validity. Do not paste tokens, passwords, certificate private keys, encrypted backup keys or recovery codes into GitHub or logs. Unauthorized or unverified accounts remain off limits.
3. Isolate the incident without deleting or truncating storage; retain redacted, timestamped event metadata, immutable audit references and hashes of approved non-secret artifacts.
4. Independently verify running tasks stopped, queue dispatch halted, reauthentication and authorization checks failed closed, alerts fired, and no secrets appeared in telemetry. Tests MUST include loss of control plane, DB unavailability, stale credentials and replay.
5. Re-enable only on verified owner decision plus independent security review and complete post-incident regression. Present state: distributed kill switch, verified revoke, real alerts and incident drills are NOTRUN/NOT_IMPLEMENTED.

## User/operator install and disaster recovery checklist (099)

Before any install: verify the exact signed release/build provenance, supported owner host CPU/RAM/GPU and disk, least-privilege service identities and networking. Never infer the owner device from GitHub runners. Demo instructions in `omega_mvi/README.md` apply only to a deliberately isolated local fixture, not production.

A genuine recovery rehearsal must use a NEW authorized isolated target: private encrypted backup manifest and checksum verified by owner, decryption key accessed outside the model and logs, incompatible schema version rejected before restore, independent integrity/data-query comparison, encrypted storage validation, strict ACL and secret scan, explicit RPO/RTO measurement, restored service denied pending independent review. Owner-local 0.1.2/0.1.3/0.1.4 backups remain **NOT_ACCESSED** here. Never move a decrypted backup into GitHub/Actions or any retrieval index.

## Recording status

Only after checking `omega-ops-recovery.yml` at its **final commit SHA** may the sentinel/backup/migration synthetic subchecks be recorded PASS. No individual passing CI proves OMEGA-093 as a whole, and NONE of the six is production DONE. Record Action run URL, job, exact checked-out SHA, PASS/FAIL/NOTRUN, reviewer, any skip, and explicitly the negative resource-safety boundary at Issue #25.
