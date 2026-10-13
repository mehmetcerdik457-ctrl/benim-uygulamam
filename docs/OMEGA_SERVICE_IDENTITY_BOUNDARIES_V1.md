# OMEGA-023/024/027 — Proposed service identity boundaries (NO LIVE GRANTS)

Status 2026-10-13: **DESIGN + SYNTHETIC CONTRACT ONLY / NOT ACCEPTED**. This is not an IAM provisioning manifest and must not be used to create production principals or credentials. This draft respects `scope.yaml`: read-only/dry-run/default-deny; permission changes require explicit scoped owner authorization.

## Non-overlapping permission map

| Fixture service | Only allowed fixture action | Only allowed fixture resource | Must never receive by default |
| --- | --- | --- | --- |
| `synthetic.inventory` | `repository:read` | `synthetic-repository-omega` | repository write, deploy, new repositories, secrets |
| `synthetic.retrieval` | `rag:read` | `synthetic-rag-omega` | cross-tenant search, raw secret retrieval |
| `synthetic.pr_review` | `pr:read` | `synthetic-pr-omega` | PR approve/merge, GitHub administration |
| `synthetic.audit` | `audit:append` | `synthetic-audit-omega` | read unredacted secrets, overwrite/delete events |
| `synthetic.backup` | `backup:fixture` | `synthetic-backup-omega` | real backup download, production restore, recovery keys |

The only permitted fixture tenant is `synthetic-tenant-omega`. An offline lease must match exactly service + action + resource + tenant and not be expired/revoked. The `omega_mvi/security/resource_boundary.py` implementation is a **test simulator**; its caller-supplied service strings are *not* trustworthy identity. `require_live_workload_authorization` intentionally always denies.

## Production design gates before any actual service principal

1. **Owner scope decision**: explicit provider/account, project/organization, exact repository/resource IDs, permission list, allowed caller, duration, environments, data classification, rotation interval and named approver. Tools being installed do not authorize broader access.
2. **Principal isolation**: nonshared workload principals and independently trusted federation; deny wildcard actions, broad root/admin roles, interactive service identities, and cross-tenant grants. Runtime task claims and LLM tool output are untrusted.
3. **Authentication**: validate real OIDC issuer/audience/signature/expiry for owner-delegated sessions (use vetted provider SDK + Authorization Code/PKCE) or provider-supported workload federation. Bind verified principals to exact permission/resource policy server-side; do not trust unsigned text or fixture JWTs.
4. **Token lifetime**: use short-lived bearer tokens from authorized issuer and supported automatic rotation with an actual provider revocation experiment. The existing five-minute fixture reference is not a provider token.
5. **Audit**: provider-side metadata-only `secret_use` records, independent append-only storage and retention/immutability with external witness anchors; never send passwords/tokens/private keys to repo, model, database, UI or logs.
6. **Negative tests**: wrong service, target, repository, project/tenant, expired/replayed token, revoked device, stale rotation generation, hostile tool output, manipulated JWT headers, provider outage, audit unavailability, fail-closed fallback.
7. **Rollout**: isolated staging first, independent security review, final code SHA-bound tests, rollback plan, explicit owner decision; no automatic merge, deployment or cross-account grants.

## Security limitations preserved

- Current PR #62 only has ephemeral fixture references, simulated resource policy, synthetic signed OIDC-shaped test claims, and synthetic encrypted recovery. It does **not** provision a real IdP, JWKS trust, workload credentials, cloud IAM, tenant-scoped ACL backend, durable provider audit or actual revocation.
- A real IAM adapter must be separately implemented, tested against only the exact owner-approved staging identity and checked for effective—not merely configured—permissions.
- The existing `main`, draft PR #58, PR #62, integrated PR #69 and private local `0.1.4-dev` are distinct code sources. New PR #62 commits are **not automatically present** in PR #69. Integration must import exact blobs under independent review.
- Production acceptance of original 23, 24, 25, 27, 29, 30 remains **NOT ACCEPTED (0/6)**.

Rollback: close the separate draft / remove only synthetic files; no owner device, cloud principal, real backup or recovery key has been changed.
