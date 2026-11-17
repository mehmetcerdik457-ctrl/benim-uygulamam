# OMEGA — Production attestation implementation contract

Status: DESIGN ONLY — NOT PRODUCTION ACCEPTED. This document does not override PR #101 or grant deployment.

## Existing verified facts
- The 100-requirement manifest currently records 100 BLOCKED requirements.
- `scripts/omega_acceptance_gate.py` deliberately returns `production_accepted: false` because it does not validate deployment receipts.
- A green inventory CI is not a production deployment.

## Release admission requirements (all mandatory)
1. Exact source commit SHA and reviewed, immutable release tag.
2. Reproducible build provenance: artifact SHA-256, builder identity, CI run URL/ID, build environment, signed provenance and dependency/SBOM inventory.
3. Owner authorization and independent auditor approval, bound cryptographically to the exact artifact digest and target environment. Distinct trusted public keys; reject self-approval.
4. All 100 original requirement receipts independently VERIFIED with matching specification hashes, test logs, device/platform identifiers and owner approvals.
5. Real isolated PostgreSQL integration suite with test discovery count, 16 previously skipped cases explicitly identified and executed; never count mock tests as real integration tests.
6. Android artifact signature, versionCode, min/target SDK, compatibility matrix and physical-device smoke evidence where required.
7. ORBA Google Play Billing end-to-end purchase, restore, cancellation, expiry, refund and RTDN replay tests in approved test environment. Server-side purchase verification and idempotent entitlement ledger. No live charge during acceptance tests.
8. Target production deployment receipt (environment, deploy ID, commit, artifact digest, timestamp and authenticated deploy actor).
9. Post-deploy smoke probes, health and dependency checks, monitoring/alert readiness, and independently verified rollback rehearsal and rollback artifact.
10. No critical unresolved security finding; owner approves production activation as a separate explicit action.

## Fail-closed verifier contract
- Input: bounded JSON manifest plus locally available immutable logs and detached signatures; no secrets committed.
- Reject: duplicate JSON keys, unknown critical fields, missing evidence, mismatched SHA-256, stale timestamps, wrong environment, unsigned receipts, invalid signatures, conflicting signer identities, reused deployment IDs and partial test coverage.
- Separate `requirements_verified`, `release_artifact_verified`, `deployment_verified`, `rollback_verified`, `billing_verified`, and `production_accepted` verdicts.
- `production_accepted` may become true only if every required gate verifies; a label, issue comment or manual override is never evidence.
- Produce machine-readable reasons for every failure and a hashable audit record. Do not automatically merge or deploy as a side effect of verification.

## Test matrix before wiring to release
- Negative: absent receipt, tampered artifact, wrong SHA, wrong public key, replay, stale receipt, incorrect environment, mismatched source commit, incomplete PostgreSQL cases, failed rollback, missing billing notification.
- Positive: independently generated test signatures over synthetic fixtures demonstrate parser and signature logic, but MUST NOT be interpreted as real production acceptance.
- Integration: staging build -> signed deployment -> authenticated smoke -> rollback -> independent review -> explicit owner-approved production release.

## Next implementation steps
1. Add `scripts/omega_deployment_attestation.py` and dedicated tests on a feature branch; retain current `production_accepted: false` until independent validation is complete.
2. Inventory real 16 skipped PostgreSQL tests and execute against disposable PostgreSQL in CI.
3. Implement immutable provenance and deploy/rollback receipt collection with trusted keys supplied only in the authorized runner.
4. Connect the verified verdict to a protected release environment with human review, not to the inventory workflow.
