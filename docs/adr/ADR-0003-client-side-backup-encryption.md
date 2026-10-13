# ADR-0003 — Client-side encrypted backup and evidence recovery

- **Status:** PROPOSED / NOT OWNER-APPROVED
- **Date:** 2026-10-11
- **Requirement:** OMEGA-005; recovery prerequisites also affect OMEGA-019/020
- **Baseline:** GitHub PR #58 head `044c558b2b28e05929a9acd79a639a32092ab187`; NOT the private `0.1.4-dev` commit `053e75d5591c836714d27d2d8b9b3f74c4464b9f`.

## Context

The Phase-0 architecture mentions encryption before an off-device backup, but an independently reviewed encryption format, key custody, recovery test and retention/expiry design are missing. Backup is **not** authorized by reading this ADR. No owner machine, Drive backup contents, keys, recovery materials or private manifest were examined.

A valid recovery plan must protect confidentiality **and** authenticated integrity even when the storage destination is compromised, while permitting an offline restore under the owner's control. SHA-256 alone detects differences but does not authenticate who made a change. Neither Drive transport encryption nor provider-managed at-rest encryption is a substitute for client-side encryption in this threat model.

## Proposed decision (gated)

1. Keep backups **disabled by default**. Require a scoped owner-approved plan specifying selected folders, classification, exact destination, storage lifecycle, key custodian, recipients, cost ceiling, RTO/RPO and deletion requirements before enabling any task.
2. Evaluate an offline-first authenticated encryption tool with established streaming format (e.g. `age` with validated recipient management) and a managed repository backup system (e.g. `restic` or `Kopia`) on non-sensitive test fixtures. **No product selected, dependency installed, credentials generated or real encryption performed.**
3. Encrypt locally *before* transport. Store the encryption identity/recovery material outside Git, RAG, prompt context, CI and backup destination. Use per-backup unique authenticated encryption parameters as specified by the chosen reviewed tool. Do not invent a custom cipher or directly construct cryptography primitives here.
4. Bind each encrypted artifact to a versioned manifest: source-ref aliases, classification, minimal ownership/ACL/retention metadata, UTC verification time, ciphertext SHA-256, tool/format version and a separate signature or authenticated manifest from an independently controlled key. Keep sensitive filenames and content hashes only in owner-private manifests, not public Issue #25.
5. Validate recovery by clean-room restore with **synthetic data**, authentication/integrity failure tests, wrong-key denial, altered ciphertext detection, version rollback/replay detection, interrupted upload handling, storage-read-denial and owner-controlled key recovery. Record exact build, command exit codes and independently verified RTO/RPO against owner-approved targets.
6. Access scope remains default-deny: this proposal does not authorize Drive, disks, cloud services, payments, key rotation, production upload or deletion. Recovery keys and actual local `0.1.4-dev` evidence remain private.

## Alternatives and trade-offs

| Alternative | Benefit | Risk / current disposition |
| --- | --- | --- |
| `age` with recipient public keys | Simple offline authenticated file encryption and explicit recipients | Key distribution, bulk incremental deduplication and restore orchestration need evaluation; **candidate, not selected** |
| `restic` or `Kopia` with client-side repository encryption | Versioned incremental snapshots, repository verification and retention options | More moving parts, metadata exposure and password/key custody; **candidate, not selected** |
| OS full-disk encryption | Protects a powered-off device | Does not necessarily encrypt the backup before cloud upload; **insufficient alone** |
| Drive transport + at-rest encryption only | Simpler operations | Provider/trust access to content and metadata; **rejected as sole control** |
| Password ZIP / 7-Zip manual archive | Familiar file workflow | Password custody, authenticated format choices and scalable restore validation vary; **not preferred pending review** |
| Home-built AES wrapper / own KDF | Full control | Severe nonce/KDF/authentication design and maintenance risks; **rejected** |

## Required approvals / acceptance

Owner selects tool and approved destinations, explicit retention, key custody and recovery approach; independent security reviewer approves threat model and encrypted format; synthetic corrupt/restore/rotation tests PASS on exact version. Until then: **BACKUP_NOT_AUTHORIZED**, **RESTORE_NOT_VERIFIED**, **NO_PRODUCTION_ACCEPTANCE**. This ADR is reversible as a documentation-only proposal; no migration or cleanup was done.
