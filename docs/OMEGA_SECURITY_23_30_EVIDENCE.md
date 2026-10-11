# OMEGA sohbet 5 — identity and secret safety (offline-only)

Date: 2026-10-11. **Not accepted**. Original requirements 23, 24, 25, 27, 29, 30 are in Phase II and remain incomplete in production. This isolated contract does not create live accounts, grant OAuth access, rotate real keys, restore a real database or read any actual backup.

## Version boundary
- Inspected GitHub draft PR #58 HEAD: `044c558b2b28e05929a9acd79a639a32092ab187` (the branch may continue moving).
- This draft builds on PR #58's head but is a **separate unmerged review branch**.
- GitHub `main`, PR #58, and private local `0.1.4-dev` at `053e75d5591c836714d27d2d8b9b3f74c4464b9f` are **different sources**; private local bytes and previous encrypted backups are NOT accessible to these tests.
- Existing `scope.yaml` defaults to read-only, dry-run, deny and forbids secret access/rotation or permission changes without separate owner approval.

## Six separate outcomes

| Original item | Current demonstrated result | Missing acceptance proof |
| --- | --- | --- |
| 23 | Five **synthetic** distinct service names and one allowlisted permission each; all cross-scope attempts fail; the existing disposable DB has `omega_demo_runtime` and `omega_demo_reader` roles, not live per-agent identities. | Real service principals, provider-side IAM assignments and tested effective authorization per worker. |
| 24 | Offline lease-reference TTL <= 5 minutes, expiry and in-memory rotation invalidate old references. The references are **not bearer tokens**. | Short-lived provider tokens, live automatic rotation, stale-session containment, provider audit evidence. |
| 25 | Closed-schema synthetic audit events accept event kind/service/outcome only, rejecting arbitrary secret fields and free text. | Durable security event sink, log pipeline leak prevention, retention/immutability, access tests. |
| 27 | `require_live_oidc` **always denies**, even JWT-shaped caller input. No trusted IdP, issuer keys, delegated session, or signature verification exists. | Owner-approved provider; exact issuer/audience allowlist; signature/JWKS verification; expiration/nonce/state/PKCE tests; authorized scope binding, revocation and durable approval checks. |
| 29 | Isolated AES-256-GCM encrypt/restore round-trip for bytes carrying explicit synthetic marker; wrong key, tamper, truncation and non-fixture inputs fail. Keys generated only in test process. | Real backup key custody outside backups; documented recovery trustees and drill; recovery of test snapshot with measured RPO/RTO; production backup inventory and integrity checks with separate scoped approval. |
| 30 | In-memory lost-device and suspected-service states revoke synthetic lease references. | Authoritative IdP/session logout and revocation; alerting/containment owners; break-glass access, communication, forensic evidence and tabletop/restore drills. |

## Target design (proposal, no live access)
- Define one non-interchangeable workload principal per GitHub inventory, retrieval, PR audit, encrypted backup and audit writer. Scopes are explicit, no wildcard or tenant-wide access.
- Use independently trusted OIDC for delegated user login (Authorization Code + PKCE) or provider-supported workload federation. Verify issuer, audience, key signature, nonce/state, expiration, permitted scopes and replay resistance at a trusted backend. Never decode unsigned client claims into `Principal`.
- Keep permission-changing and secret-reading capabilities disabled until the owner approves the **exact provider, resource, identity, permission and duration**, with revocation/rollback and an independent review. No production API route in this PR imports the offline fixture.
- Keep secret material outside LLM/logs/Git/RAG. A log event receives only closed-vocabulary labels; do not log exception text or request bodies.
- Encrypt client-side before any permitted backup upload, keep keys independently, authenticate ciphertext and bind restore to an isolated sentinel-validated target. **Do not touch existing 0.1.2 / 0.1.3 / 0.1.4 encrypted backup sets.**
- Record device-loss/suspicious-access playbooks with owner-approved termination of sessions and provider tokens only after authenticating the requester. Default to contain/deny for offline tests.

## Isolated evidence
```sh
python -m pip install -r omega_mvi/requirements-test.txt
PYTHONPATH=.:omega_mvi python -m pytest -q tests/test_omega_security_offline.py
```
Before the review-branch publication, the same isolated source files were executed locally: **7 passed**, no real account, network calls or recovery keys. This is not a GitHub Actions result. Re-run at the final review-branch full SHA and inspect its workflow logs.

Rollback: close draft PR and delete only its isolated branch. No live permissions, secret values, databases or backups are modified.

## Incremental continuation: offline signed-claim adversarial test expansion

- Added `omega_mvi/security/oidc_fixture.py` and `tests/test_omega_oidc_fixture.py`: verification of **test-only** Ed25519-signed JWT-shaped claims using a fixed `.invalid` issuer, exact audience, finite synthetic key allowlist, issuer/audience/scope/nonce/time checks, in-memory replay rejection and PKCE S256/state comparison.
- Negative test cases include `alg=none`, `alg=HS256`, attacker-supplied `jku`/`jwk`, wrong signing key, wrong audience/issuer/nonce, expired/future claims, oversized lifetime, replay, audience confusion, different scope and corrupted JWT. Real `require_live_oidc()` **continues to deny** even a valid signed fixture.
- Tightened `restore_synthetic_backup` envelope upper bound before attempting AES-GCM decryption and added a negative oversized-input test. This is not a real database restore or recovery-key test.
- Added `.github/workflows/omega-security-fixtures.yml`: test-specific read-only GitHub Actions job, no production secrets, pinned actions and test dependencies; runs the two fixture suites without relying on skipped database tests.
- Local isolated test command: `PYTHONPATH=. python -m pytest -q -ra tests/test_omega_security_offline.py tests/test_omega_oidc_fixture.py` → **29 passed**, no skipped tests. The authoritative GitHub Actions workflow results must still be checked at the final exact HEAD SHA after this documentation change.
- **Critical limitation:** This intentionally hand-scoped simulator is *not a reusable production JWT/OIDC verifier*. A true implementation must use vetted IdP libraries, real provider configuration, remote JWKS lifecycle and key rotation, secure session handling, durable replay and revocation, resource-level authorization and human approval. None are activated by this PR.

Security acceptance remains **NOT ACCEPTED (6/6)**; the six requirement statuses in the authoritative matrix remain unchanged. Test progress does not indicate production readiness.
