# PROJECT OMEGA — Phase 0 Scope Conflict Review

**Status:** DRAFT — independent proposal; not an authorization or approval
**Reviewed:** 2026-10-11
**Purpose:** Compare the proposed `scope.yaml` in [PR #19](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/19) and [PR #21](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/21) with the repository's current roadmap, state, and security policy.
**Evidence basis:** PR #19 head `9150a92bb68eaf4609d0d237cb492e918e7d1c21`; PR #21 head `b84f3b44569fd356e8185c71c4f8daea8963e72d`; baseline documents on the repository's `main` base commit `75cc6109944689522bf261b5d64fdaa6bc5c9c79`.

This review is documentation only. It does not edit either draft `scope.yaml`, change repository settings or grants, access integrations, or authorize implementation. PR descriptions and scope files are proposals, not effective permissions. Repository-document statements below are recorded claims, not independent verification of repository settings or runtime state.

## Draft comparison

| Area | PR #19 proposal | PR #21 proposal | Review |
| --- | --- | --- | --- |
| Default policy | Read-only, dry-run, default deny (`scope.yaml:3–6`) | Same, and explicitly labelled `proposed_read_only_discovery` (`scope.yaml:3–7`) | Equivalent safety defaults; neither draft is itself an enforcement mechanism. |
| GitHub repositories | Reference repository read-only, but permits metadata discovery in additional repositories (`scope.yaml:18–21`) | Names this repository, allows reading repository content/current metadata, and denies additional repositories (`scope.yaml:19–23`) | PR #19 is broader. Its approval list says `cross_repository_write`, not cross-repository read (`scope.yaml:7–17`); therefore its metadata discovery is not clearly gated. PR #21 is the safer boundary, though its content allowance is not path-limited. |
| Google Drive | Metadata-only access; backup disabled until client-side encryption is verified (`scope.yaml:22–25`) | Access denied and contents not accessed (`scope.yaml:24–26`) | PR #19 grants unnecessary metadata access for this review. PR #21's deny is appropriate. |
| Google Cloud and local device | Denied until separately scoped; device marked not connected (`scope.yaml:26–31`) | Denied; owner hardware marked unknown (`scope.yaml:27–31`) | Both deny access. PR #21 makes the unknown owner-hardware status explicit. |
| Secret values | Forbidden in repository, logs, LLM context, and index (`scope.yaml:32–40`) | Same (`scope.yaml:34–42`) | Retain these prohibitions. Approval language must never be treated as permission to retrieve secret values. |
| Runner observations | No owner-device disclaimer | Says runner observations do not apply to owner device (`scope.yaml:32–33`) | PR #21's explicit limitation is safer; runner observations are not owner-device evidence. |

## Baseline evidence and implications

| Source | Evidence | Scope implication |
| --- | --- | --- |
| [`AI_MASTER_ROADMAP.md`](../AI_MASTER_ROADMAP.md) | Phase 0 calls for repository hardening, secret protection, branch rules, and a decision on public visibility (`lines 17–27`). Later phases describe model/provider, research, owner identity, phone bridge, CI/CD, and operations work (`lines 29–135`). | These are goals and future work, not grants to access other repositories, Drive, Cloud, devices, providers, or to make changes. |
| [`CURRENT_STATE.md`](../CURRENT_STATE.md) | Records model/research providers and owner crypto as not provisioned, phone bridge as not implemented, branch protection off, and repository public (`lines 19–25`). It names `REAL_AI_BACKEND` as the next gate and says not to reopen the closed PWA gate without an affecting change (`lines 27–31`). | Keep this review bounded to the requested scope and baseline documents. The stated settings/status have not been independently verified here. |
| [`SECURITY.md`](../SECURITY.md) | Says not to publish exploitable vulnerability details publicly and never to commit secrets, tokens, keys, credentials, or private datasets (`lines 3–8`). | Do not retrieve, quote, or publish secret values or exploitable details. A separate approval gate does not override these prohibitions. |

## Consolidated minimum-rights proposal

This YAML is a proposed policy excerpt in this document only. It does not replace, edit, or grant permission through either existing `scope.yaml`. Its read allowance is limited to the evidence needed for this review; any expansion needs separate, explicit owner approval before access.

```yaml
schema_version: "1.0"
project: PROJECT_OMEGA
status: draft_requires_owner_approval
policy:
  default_mode: read_only
  dry_run: true
  default_decision: deny
  allowed_read_inputs:
    - "PR #19 and PR #21 scope.yaml drafts"
    - AI_MASTER_ROADMAP.md
    - CURRENT_STATE.md
    - SECURITY.md
  writes: denied
  secret_values: never_access_or_disclose
github:
  allowed_repository: "mehmetcerdik457-ctrl/benim-uygulamam"
  additional_repositories: denied
  settings_or_permission_changes: denied
google_drive: denied
google_cloud: denied
local_device: denied
model_or_research_provider_calls: denied
external_side_effects: denied
deployment_merge_or_payment: denied
approval:
  owner_approval_required_before_adoption_or_scope_expansion: true
  approval_is_not_authorization_to_access_secret_values: true
validation:
  production_ready: false
```

The allowance above is a proposed task boundary, not a claim that GitHub enforces path-level read permissions. Effective access and branch protection were not independently verified; the roadmap and current-state file say branch protection is off. No access beyond the requested public repository documents is necessary to resolve this conflict.

## Owner decision required

Keep this proposal in DRAFT until the repository owner explicitly approves or revises it. In particular, decide whether to adopt PR #21's single-repository/Drive-deny boundary, narrowed further to the listed review inputs. Do not infer approval from this review, the existence of either draft, or the repository's public visibility. Any later request for other repositories, Drive, Cloud, devices, external providers, write access, or side effects needs a separate, narrowly scoped approval; secret values remain prohibited.
