# PROJECT OMEGA — bounded external inventory (specialist 4)

Date: 2026-10-11. Scope: original requirements **11, 12, 13, 17, 18**.
**Proposal only / NOT ACCEPTED / no deployment.** Public GitHub branch and
separate private 0.1.4-dev commit 053e75d5591c836714d27d2d8b9b3f74c4464b9f
are different code bases. The latter was **not accessed or tested**.
Central non-secret reporting location: [Issue #25](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/issues/25).

## Permission boundary / measured observations

- GitHub connector authenticated as repository owner with read access to
  `mehmetcerdik457-ctrl/benim-uygulamam`. This is **not** an authorization
  to grant Copilot access to other repositories or modify GitHub policies.
  Repo observed public, main default. The REST branches endpoint returned
  **46 on page 1, zero on page 2** (2026-10-11, per_page=100);
  source repository reported **forks_count=0**. Direct forks-list request
  was rejected by connector, so **fork enumeration NOT VERIFIED**.
  No rate-limit response headers or live quota measurement exposed by the
  connector: **quota UNKNOWN**. Do not assume arbitrary future pagination
  complete, or infer access to all repos from owner status.
- `scope.yaml` currently denies external APIs and all cross-repository
  discovery by the *agent*. This task's narrowly requested inventory reads
  do not mutate agent policy or confer runtime permissions. Any production
  connector needs an exact approved-resource allowlist and owner decision.
- Google Drive connection could read the specifically supplied OMEGA master
  specification (a single document). No Drive **folder allowlist** was
  supplied or authorized for discovery: folder inventory **UNKNOWN / NOT RUN**.
  Do not traverse the document's parent folder based only on its parent ID,
  or assume access to other 476/457 resources. No bytes downloaded.
- Google Cloud project, Compute instance, disk, snapshot, IAM scope, billing,
  subscription and cost inventory: **UNKNOWN**. No GCP project authorization
  or Google Cloud inventory API connection verified. No discovery, changes,
  machine deletion, paid services, or credential probing attempted.

## Implemented isolated, provider-neutral safety helpers

`omega_mvi/inspection/external_accounts/__init__.py`:
- `github_metadata_pages`: exact repository allowlist, `branches` or
  `forks` metadata only, bounded 100-item pages, sanitized Link-next with
  same origin/resource and exact sequential cursor, rate-limit/error and
  ambiguous-full-page handling fail closed, no automatic retry or raw response
  logging. The API adapter is supplied by caller; this code **does not**
  connect to GitHub or establish API quotas.
- `drive_metadata_only`: mandatory exact folder ID allowlist,
  previously obtained **complete** metadata pages, verified direct parent,
  in-memory ID/MIME projection and MIME counts only. No names, owners,
  permissions, descriptions, file bytes or downloads. New
  `drive_metadata_pages` checks every provider page for explicit
  `incomplete_search=False`, exact folder-parent membership, bounded
  next-page tokens, no repeated items/tokens, and returns **only aggregate
  MIME counts**, never file IDs or page tokens. The adapter must map
  Google Drive's `incompleteSearch` and `nextPageToken` fields and must
  itself prove the exact folder query and least-privilege OAuth scope;
  **live Drive pagination is not connected**. Metadata may itself be
  sensitive: never print raw IDs in public issues/logs/RAG/LLM.

`omega_mvi/inspection/external_accounts/secret_findings.py`:
- Maps detector identifiers (hints, NOT actual validity checks) to GitHub,
  GitLab, Google Cloud, AWS, OpenAI, Slack and Hugging Face, with UNKNOWN
  for unrecognized identifiers.
- Fixed-field finding: provider type, normalized relative source path and
  line, explicit risk (including UNKNOWN), remediation state and
  SUSPECTED_UNVERIFIED classification. **No secret match, raw token, hash
  or password fields.** Records are created only from pre-classified detector
  IDs; the module performs no scanning itself.
- Verified remediation states (`REVOKED_VERIFIED`, `ROTATED_VERIFIED`,
  `FALSE_POSITIVE_VERIFIED`) are **impossible to set** through this
  untrusted helper, even if a caller asserts `owner_approved=True` and
  `provider_verified=True`. These are forgeable booleans, not proof.
  An independent owner-private provider-attestation mechanism is a
  prerequisite. The module does not call any provider API. Actual verified
  status remains **UNKNOWN** for all real accounts.

## Official manual rotation / revocation playbooks (OMEGA-018)

**No action below was executed.** A suspected leak must first be triaged by
the resource owner in the provider's trusted control plane, with no token
copied into a ticket, model context, CI log or validation API call.
Distinguish *suspected* pattern, *confirmed compromised*, *replaced* and
*revoked*; never promote states solely from pattern matches.

1. **GitHub PAT / OAuth / app token:** Identify token owner and app category;
   prepare a least-privilege replacement via GitHub Settings and update
   consumers in their approved secret stores; use the corresponding GitHub
   token or app authorization revocation control. Review active
   integrations/audit trail. Note that GitHub's "Revoke all" page
   describes **enterprise-wide bulk/SSO actions**, not ordinary PAT
   revocation; do not select bulk controls for one leaked PAT.
   [GitHub personal access token management](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens),
   [token expiration/revocation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation),
   [emergency bulk revocation (separate, high impact)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/revoking-your-credentials).
2. **Google Cloud service account key:** Prefer keyless workload federation
   where applicable. Owner scopes service account and workloads, arranges
   replacement, updates consumers, **disables** old key, tests business
   traffic with sanitized results, then removes old key with separate
   approval. Key disable/delete does **not** revoke already issued short-lived
   credentials. [Google key rotation](https://docs.cloud.google.com/iam/docs/key-rotation),
   [disable key](https://docs.cloud.google.com/iam/docs/keys-disable-enable),
   [delete key](https://docs.cloud.google.com/iam/docs/keys-create-delete).
3. **Google API key:** Determine actual owning project and restriction
   policy; owner uses Credentials > key > Rotate, verifies restrictions,
   updates consumers, then deletes old key when safe. Rotate via UI is not
   equivalent to immediate unconditional deletion.
   [Google API key rotation](https://docs.cloud.google.com/docs/authentication/api-keys).
4. **AWS IAM access key:** Owner scopes IAM identity, creates authorized
   replacement only if needed, updates secret stores, deactivates old key,
   checks application operation, then deletes unused old key. Treat root
   credentials and other credential types separately.
   [AWS IAM guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-key-self-managed.html).
5. **OpenAI API key:** Owner identifies affected project, creates a new
   project-scoped key as needed, updates consumers, then uses API Keys page
   to delete old key. Deletion can break dependents.
   [OpenAI exposed-key guidance](https://help.openai.com/en/articles/8304786-keeping-your-openai-account-secure).
6. **GitLab personal/project token:** Owner selects exact token type
   and uses the corresponding token Rotate/Revoke controls. Rotation
   invalidates the previous token immediately and requires consumer
   updates. [Personal tokens](https://docs.gitlab.com/user/profile/personal_access_tokens/),
   [project tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/).
7. **Slack app OAuth token:** Owner inventories installed app and token
   lifecycle, uses supported expiring access + refresh-token rotation
   rather than assuming generic PAT semantics. Confirm app-specific
   revocation mechanism before any action.
   [Slack official guide](https://docs.slack.dev/authentication/using-token-rotation/).
8. **Hugging Face user token:** Owner uses Settings > Access Tokens to delete
   or refresh an exposed token and updates consumers. Do not send raw
   suspect tokens to the optional public revocation endpoint.
   [Hugging Face tokens](https://huggingface.co/docs/hub/main/en/security-tokens).

Approval record for any provider: exact provider, account/workload identifier
stored privately, purpose, blast-radius assessment, owner approval, safe
rollout/rollback, sanitized verification, and *separate* audit evidence.
Store in a secured owner-controlled system, **not** this public repository.

## Evidence / unresolved acceptance gates

- Synthetic tests: `tests/test_omega_external_accounts.py`: allowlist,
  cross-repo denial, Link validation and two-page behavior, rate-limit
  fail-closed, Drive parent isolation and no byte/title projection,
  provider-incomplete-search and duplicate-token detection, provider
  mapping, risk and remediation status guards, forged verified-state denial.
- This code is not yet a live GitHub/Drive production integration. Must
  independently review the exact commit, run branch CI and verify no
  other specialists' files changed; obtain explicit owner approval before
  merging, connecting to other accounts, or declaring DONE.
- OMEGA-011: **PARTIAL** (live target metadata, offline integration tests;
  fork API/list and rate limit headers not fully verified).
- OMEGA-012: **UNKNOWN / NOT RUN** (no GCP permission established).
- OMEGA-013: **PARTIAL CODE / LIVE UNKNOWN** (scope-safe, two-page tested
  metadata-only helper, no explicitly approved real folder and no live
  folder listing or OAuth scope verification).
- OMEGA-017: **PARTIAL** (schema and synthetic tests, no actual secret scan
  finding and no real provider confirmation).
- OMEGA-018: **PROCEDURE DRAFT** (official instructions cross-checked
  2026-10-11; no actual rotations or revocations; forged boolean-only
  `VERIFIED` transitions blocked; no owner/provider approval proof).
