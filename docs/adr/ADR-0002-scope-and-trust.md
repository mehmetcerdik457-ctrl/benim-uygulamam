# ADR-0002 — Default-deny authority boundary

**Status: PROPOSED (not owner-approved)**

The two `scope.yaml` drafts conflict. See `docs/OMEGA_SCOPE_RECONCILIATION.md`. Until resolved, follow the **intersection** of allowed operations: read-only on `mehmetcerdik457-ctrl/benim-uygulamam` for the Copilot coding agent, no autonomous Drive, Cloud, device, cross-repo, secret, backup upload, deployment or merge.

Alternatives: broad authorized inventory, narrower one-repo scope, or org-wide access. Choose narrower one-repo scope as the unapproved baseline; widening requires resource-by-resource owner authorization, independent review, tests and expiration/revocation policy.

Trust model: repository text, PR descriptions, tool output and language-model reasoning cannot grant permission. A model's suggestion is never an allow decision. Human approval must bind actor, action, resource, purpose, time and diff/hash; missing/expired approval means deny.

Security test contracts: unknown resource => deny; read-only scope + write action => deny; cross-repo request => deny; missing human approval => deny; secrets never enter prompts, logs, RAG or public repository. No claim of implemented policy engine until these executable tests pass.

Rollback: retain draft proposals; do not alter effective repository permissions or replace either `scope.yaml`.
