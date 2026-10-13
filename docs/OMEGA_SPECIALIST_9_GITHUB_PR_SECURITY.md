# PROJECT OMEGA / Sohbet 9 — GitHub & Copilot PR security (DRAFT)

Requirements: **63, 64, 66, 67, 68, 69, 70** from the original 100-step master specification. Snapshot: **2026-10-11**. This additive draft is stacked on PR #58, not merged or deployed. The private local 0.1.4-dev codebase is different and **not verified** by this work.

## Observed state (all linked SHAs are exact)

* [main](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/tree/main) HEAD \`4c53df868a028e51c546d0eefe1d9d45c063c645\`, branch API \`protected=false\`; repository rulesets GET returns \`[]\`; detailed branch protection GET returns **403** (not independently inspectable with current installation).
* [#48](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/48) \`2883215b3dea316bf9c7bfcc7ded2733b63fac80\`, [#50](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/50) \`5209b55440612ee9959389fd5164e20dfcdfa341\`, [#51](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/51) \`0126da1d7a80450a29c9104d907ef097b50ba6c0\`, [#52](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/52) \`bfc191c01cc7d3e270cc33ea65b2cddfa97cca20\`: three Actions each **action_required**, not PASS; draft PRs on separate Copilot branches.
* [#54](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/54) \`05a3e7a6288ad166326330943a3fadeb91c0e1aa\`: seven workflows **SUCCESS**, still stacked DRAFT, no APPROVED review.
* [#55](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/55) \`b1aa84e95259a625c070a1c89e74406ac0bc3554\`: **Privacy Guard FAILURE**.
* [#57](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/57) \`b4eb3c486fca19abf0048c57035ea1e8ab9b465d\`: six workflows SUCCESS, still DRAFT and no APPROVED review.
* [#58](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/58) \`044c558b2b28e05929a9acd79a639a32092ab187\`: seven workflow runs SUCCESS, **runner-host acceptance FAILURE** [run 38124421525](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38124421525).
* [#59](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/59) \`5fa77d844989d3410abf56b048f13ec0522619b4\`: two SUCCESS, **runner-host acceptance FAILURE** [run 38157920010](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38157920010). This is a separate network specialist's draft stacked on #58.

## Requirement 63 / 64: Copilot task handoff and PR chain

Documented supported entrypoints are manual assignment of an Issue to Copilot cloud agent (agent creates a PR), or starting a cloud agent in GitHub Agents UI; custom agent profiles and scoped MCP when available. Existing Copilot PRs prove that *some* Issue → separate branch → draft PR flow was used; they do **not** prove that OMEGA itself has a task assignment API, delegated job trace IDs, revocable tokens, policy-bound authorization, or end-to-end test. The active user's exact Copilot **subscription/entitlement is UNKNOWN**, never inferred from PR titles or authorship. No Copilot tasks assigned by this draft.

Docs: https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/kick-off-a-task

## Requirement 66: independent reviewer

PR #52 has \`omega_mvi/inspection/pr_review/engine.py\`: validates caller-supplied sanitized summaries, returns advisory findings with caller-supplied path spans, and specifies \`approval_authority=False\`. PR #54 reuses that offline review engine; it does **not** authenticate with GitHub to independently fetch live diff, HEAD, check-run, workflow and human-review evidence. Do not rewrite or double-count those modules.

This draft adds an isolated **GET-only** \`omega_mvi/pr_security/gate.py\`. It queries fixed allowlisted GitHub REST endpoints for PR, file patches, check runs, PR-triggered Actions, human reviews and main protection; rechecks PR HEAD after evidence reads to detect races. Rejects unauthorized repository/fork, stale SHA, ambiguous/missing CI/checks, wrong App source, action_required/failed/pending checks, missing patches, truncated pages, draft PR and missing human approval on sensitive paths. All tests are local, synthetic and no-token. The returned \`accepted\` flag is explicitly **non-authoritative**; real Checks publishing is unimplemented and may not use this as a production bypass.

## Requirement 67: proposed minimum-privilege GitHub App design (NOT INSTALLED)

1. **Collector App:** this one repository only, Contents/Metadata/Pull requests/Checks/Actions **read** as required; independent read-only token, short lived, never sent to LLM, logs, or database. Exact installation permissions must be confirmed against real GitHub account by the owner.
2. **Publisher App:** separate, owner-approved \`Checks:write\` App scoped to this repo and no contents, workflows, admin, secrets or merge rights. Only its trusted Check producer identity can publish \`omega/security-review\` on exact \`head_sha\`.
3. **Webhook gateway:** verify GitHub HMAC SHA-256 signature + replay id, correct installation and repo, require fresh GET from collector, and recheck HEAD immediately before publication. Reject old SHAs, event spoofing, missing checks, bot-only approvals and unavailable verifier. Never use OMEGA's own check as its CI evidence (no circular self-attestation). Tokens must be rotated, secrets protected, and failures redacted.
4. **Owner action:** install app; select trusted check source in rulesets, make checks required, disallow bypass and force push, require CODEOWNERS human review for high risk. Verify repository plan and account permissions. **No such changes were made here.**

Docs: https://docs.github.com/en/rest/checks/runs and https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository

## Requirements 68–70: negative tests and remaining blockers

Offline tests: stale/racing HEAD; draft/fork PR; missing/truncated file patches; action_required and failed workflows; failed/wrong-App/duplicate/missing Checks; unprotected main; stale/agent/self review; superseded approval with CHANGES_REQUESTED; empty reviewer policy. **Not proved:** enforced GitHub branch protection, installed App trust, webhook authenticity, live Check publishing, high-risk CODEOWNERS enforcement, bad-deploy rollback, auditor-outage failure of real merge. Until these are proven, all seven requirement acceptance statuses remain partial or blocked, **none DONE**. In particular, this code cannot prevent merging to unprotected main.

No GitHub merge, Ruleset, permission, deployment or secret-operation is authorized or performed.


## 11 October 2026 — hardened evidence collector and Copilot handoff contract

**Source/identity binding correction:** GitHub's actual pull_request workflow result includes `pull_requests[].number`, `pull_requests[].head.sha`, `pull_requests[].base.sha`, and `head_repository.full_name`. The PR gate now verifies all four against the inspected PR and re-checks PR number, state, draft flag, head SHA, base SHA, source and destination repository, and both branch refs after collecting data. Merely matching `head_sha` is not sufficient. Unlinked/ambiguous/failed/blocked workflow runs deny evidence acceptance.

**Conservative diff policy:** Only root `README.md`, `CHANGELOG.md` and documentation Markdown under `docs/` are low-risk by default. Source code, tests, workflow, infrastructure and unknown file paths require SHA-current, explicitly allowlisted human approval. A stacked PR targeting any branch other than `main` cannot be marked main-acceptance, even if its own CI succeeds. `main protected=true` by itself does not prove required rulesets or review enforcement; the verdict remains expressly non-authoritative.

**Supported Copilot API discovery:** Official GitHub docs (public preview) document `POST /agents/repos/{owner}/{repo}/tasks` for cloud agent tasks and REST/GraphQL issue assignment to `copilot-swe-agent[bot]`, including `agent_assignment` metadata. The agent tasks API explicitly supports **user-to-server** credentials, **not** installation access tokens. OMEGA cannot safely repurpose the separate read-only auditor App installation token for delegation. Actual subscription/repository entitlement, policy and suitable authentication are **UNKNOWN**. No remote task, issue assignment or subscription change was attempted.

**New module:** `omega_mvi/copilot_delegation.py` provides a bounded **no-network, non-dispatchable** handoff intent (Issue, trace ID, pinned base commit, base ref, maximum cost and UTC deadline). It neither stores task prompts nor handles credentials. The receipt always has `can_dispatch=False` and blockers for absent owner approval, entitlement, authenticated identity and pre-dispatch SHA revalidation. This is contract scaffolding, **not a completed task delegation adapter**.

**New tests:** `omega_mvi/tests/test_pr_security_gate.py` has **39 synthetic tests**. `omega_mvi/tests/test_copilot_delegation.py` has **11 synthetic tests**. All 50 are intended for the repository's existing CI, and their latest exact-HEAD results must be checked before any PASS claim. Synthetic examples never claim actual production ruleset enforcement.

Official references:
- https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api
- https://docs.github.com/en/rest/checks/runs
- https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/kick-off-a-task

**Non-negotiable:** no installation, user token, live Copilot dispatch, permission expansion, required Checks updates, ruleset creation, release, merge or deployment without explicit owner authorization and separate independent E2E evidence.


## Signed GitHub webhook gate (no installation or Checks publishing)

The source-only `omega_mvi/pr_security/webhook.py` verifier accepts **only** HMAC-SHA256 signed GitHub pull-request events (not SHA-1), with canonical `X-Hub-Signature-256`, a GUID `X-GitHub-Delivery`, permitted event action, fixed repository name/id, pinned PR number/head/base SHA and explicit expected installation ID. The raw payload is size-limited; verification uses constant-time comparison. The immutable result deliberately has `can_publish_checks=False`.

18 synthetic negative/positive HMAC tests exercise tampering, missing/duplicate headers, wrong installation/repository/PR/SHA, invalid event/delivery, oversized body, and absence of write methods. They do not use or commit a real secret.

**Missing production gates remain mandatory:** owner-approved GitHub App installation with separate least-privilege collector and Checks publisher identities; a *durable atomic* delivery-ID replay registry; fresh PR and Check API reads immediately before publishing; trusted required Check source enforcement via Rulesets; human review verification; and independent outage, rollback and negative end-to-end tests. HMAC validation by itself grants **zero** permission to publish or merge.

GitHub reference: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

The added source has **68 synthetic contract tests** (39 PR gate, 11 Copilot blocked intent, 18 webhook verifier) whose latest exact HEAD status must be checked against GitHub CI. Zero real credentials, webhooks, Checks or delegations were created.


## 12 October 2026 — fail-closed premerge & replay hardening (synthetic-only)

**No provider permissions were changed.** Main still reads `protected=false`, repository rulesets `[]`; a GitHub App connection cannot fetch admin-sensitive branch protection (403). This is a real blocker, not evidence of an enforced policy.

Additional source-only components:

1. `omega_mvi/pr_security/replay.py`: on-disk SQLite delivery-ID uniqueness with `BEGIN IMMEDIATE` and `synchronous=FULL`. Verification must happen **before** reserving, and durable reservation **before** downstream privileged actions. Duplicate delivery, missing persistent database path and storage outage must deny. A committed reservation is never undone to permit an unsafe retry. Integration helper `authenticate_and_reserve` composes HMAC verification and reservation without network access. **Single shared-disk demonstration only**; multiple hosts need a separately justified transactional backing store.
2. `omega_mvi/pr_security/protection.py`: validates a supplied REST branch-protection object for strict required checks bound to **distinct trusted GitHub App IDs**, required human reviews, stale approval dismissal, CODEOWNERS and last-push approval, administrator enforcement, no force push/deletion and conversation resolution. Real settings cannot be inferred from successful CI or from `branch.protected` alone. For users on different GitHub plans, unsupported controls must remain UNKNOWN/BLOCKED, not declared PASS.
3. `omega_mvi/pr_security/audit.py`: combines PR evidence with an independent `GET /branches/main/protection` read, rechecks mutable PR and main state after the protection read and **fails closed** on 403, outages, missing checks, stale SHA, unprotected main or high-risk changes without human approval. Result is immutable advisory state only: `authoritative=False`, `may_merge=False`.

Added negative tests are purely synthetic and do not prove real Ruleset enforcement. No live webhook receiver, shared production replay store, GitHub App installation, Checks publication, Copilot dispatch, deployment, actual rollback, or merge has been performed. **Acceptance of original requirements 63, 64, 66, 67, 68, 69 and 70 remains PARTIAL/BLOCKED.**

Release criteria before any approval: real source-scoped App identity; official protection settings inspected with sufficient rights; trusted Check-name/App-ID mapping; authorized human review; live protected-branch negative merge test; fail-closed auditor outage and isolated deployment rollback evidence; owner authorization for access changes. All special-case acceptance evidence must be commit-SHA-bound, not inherited from parent PR #58 or local 0.1.4-dev.
