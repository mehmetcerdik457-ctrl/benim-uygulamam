# PROJECT OMEGA — Phase 0 Discovery

**Status:** PARTIAL — bounded repository discovery only
**Date:** 2026-10-10
**Scope:** `mehmetcerdik457-ctrl/benim-uygulamam`; no other repositories or owner devices
**Specification reference:** Draft [PR #19](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/19); its specification and `scope.yaml` are proposals, not merged policy.

## Boundaries and evidence

This is a read-only discovery record. No application code, credentials, secret values, external account inventories, cloud resources, or user data were accessed or changed. The only external read was draft PR #19 for the supplied specification. No model provider API call, deployment, permission change, key rotation, merge, or other external side effect was performed. Findings below distinguish repository statements from independently measured facts. The working environment is a hosted Linux runner, not evidence about the owner's computer or production environment.

The working tree contained 18 tracked files at discovery time:

| Area | Inventory |
| --- | --- |
| Project guidance | `README.md` (short template notice), `AI_MASTER_ROADMAP.md`, `CURRENT_STATE.md`, `SECURITY.md` |
| Backend | `backend/server.py`, `backend/README.md`, `requirements.txt`, `start.sh` |
| Tests | `tests/test_backend_contract.py`, `tests/test_placeholder.py` |
| GitHub configuration | `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/dependabot.yml`, `.github/workflows/ci.yml`, `.github/workflows/master-roadmap-guard.yml`, `.github/workflows/privacy-guard.yml` |
| Repository metadata | `.gitignore`, `.env.example` (name only; contents not inspected) |

No tracked frontend source, Docker Compose file, Makefile, license file, root `AGENTS.md`, or OMEGA master specification was present in this working tree. The master specification and proposed `scope.yaml` were read from draft PR #19, not treated as files already present here. The repository documentation declares a public repository and disabled main-branch protection; those declarations were not independently verified against repository settings.

### Runtime observations

Read-only inspection of this hosted runner reported Linux x86_64, Python 3.12.3, 4 online vCPUs, about 15 GiB RAM and no available `nvidia-smi` GPU query. Disk figures describe the runner's mounted filesystem, not owner storage. Network reachability, owner hardware, GPU/VRAM, device inventory and production runtime were not tested. These observations must not be used to size or claim support for a user deployment.

## Current architecture and gaps

- The existing application is a browser/PWA-oriented project with a Python standard-library HTTP backend. `start.sh` runs `backend/server.py`; `requirements.txt` says the backend uses only the standard library.
- The backend exposes health, provider/model and status endpoints plus chat and fail-closed research endpoints. Chat calls the hosted OpenAI Responses API when an environment credential is configured; this is not a local-first inference path. No provider call was made during discovery.
- Backend policy and operational status remain inconsistent with the OMEGA draft: the existing roadmap prioritizes a real hosted AI backend, while the draft specification prioritizes local-first operation and provider independence. Resolve this before selecting an implementation architecture.
- There is no database, task queue, local model adapter, inventory service, web admin application, or deployment description in the tracked inventory.
- Tests use pytest and currently cover response parsing, attachment metadata filtering, rate limiting and provider configuration; one test is a placeholder. CI delegates baseline and privacy checks to reusable workflows in another repository. The reusable workflow internals and latest CI run were not examined.
- `CURRENT_STATE.md` claims the PWA runtime acceptance is closed and several capabilities are unprovisioned. These are recorded claims, not re-tested acceptance evidence.

## Data classification

| Class | Examples and handling |
| --- | --- |
| **Public** | Public repository source and explicitly public metadata. Review before copying into another system. |
| **Internal** | Project planning, task records, non-public operational metadata. Keep within approved project scope. |
| **Confidential** | Private source, account/resource inventories, user data and non-public logs. Do not collect in Phase 0. |
| **Restricted** | Passwords, API tokens, private keys, recovery codes and secret file contents. Never retrieve, print, commit, index, or pass to a model. Store references only if a later approved design requires them. |

Classification is provisional: data owners, retention periods and access controls have not been established.

## Threat model

**Assets:** secret values and references; private source and user data; GitHub identities, repositories and permissions; model prompts/responses; integrity of code, builds and evidence; availability and cost of any future provider.

**Trust boundaries:** public Git content/issues/PRs to agent context; browser to backend; backend to external model provider; CI in this repository to reusable workflows in another repository; hosted runner to owner device/cloud accounts (no trust or access is assumed).

| Threat / scenario | Risk | Phase 0 mitigation and remaining gap |
| --- | --- | --- |
| Secret disclosure through repository, logs, prompts, reports, or accidental inspection | Credential theft, account takeover, private-data exposure | Did not inspect `.env.example` contents or runtime environment values; documented no-secret handling. No complete history/deployment secret audit performed. |
| Prompt injection in issues, PRs, source, provider output, or tool results | Agent follows untrusted instructions or leaks/changes data | Treat all such material as untrusted; default deny and human approval are proposed. No enforcement mechanism or adversarial tests exist in this discovery task. |
| Malicious PR or compromised dependency/workflow | Code execution, supply-chain compromise, poisoned test/evidence | CI workflow references reusable workflows by commit SHA; provenance, review controls and their implementation are not verified. No dependency or workflow execution was performed. |
| Excessive permissions or mistaken authorization | Cross-repository access, destructive writes, deployment | Limit this proposal to read-only metadata for this repository; no owner permissions inferred from tool availability. Actual GitHub grants and branch rules remain unknown. |
| External provider exposure | User prompts leave the local environment; provider retention/policy may apply | Existing backend can send chat to a hosted provider when configured. Do not send data in Phase 0; provider privacy, retention and approval are unresolved. |
| Spoofed forwarding header / rate-limit bypass | Request abuse or resource exhaustion | Backend derives its rate-limit key from `X-Forwarded-For`; only trust a proxy that sanitizes this header. Proxy configuration and internet exposure are unknown. |
| Inaccurate environment assumptions | Unsafe or infeasible deployment choices | Runner hardware observations are explicitly not owner-device facts; keep hardware, costs and service availability UNKNOWN until measured with approval. |

## Architecture decisions (Phase 0)

1. **ADR-001 — Bound discovery to this repository and read-only evidence.** Do not enumerate other private assets or make external changes. Alternatives such as organization-wide or device-wide discovery require separately scoped owner approval.
2. **ADR-002 — Adopt local-first, privacy-by-default as a target, not as a claim about current behavior.** Existing hosted-provider chat conflicts with that target. Defer model/provider selection until the owner chooses local-only, hosted, or an explicitly consented hybrid policy. A fully hosted model is simpler but does not meet the draft's local-first/privacy goals by default.
3. **ADR-003 — Preserve the existing Python standard-library backend during discovery.** It is the only backend currently inventoried. Do not introduce FastAPI, a database, containers, a queue, or other infrastructure until a justified ADR and bounded MVI scope exist; compare standard-library continuation with FastAPI and operational alternatives at that point.
4. **ADR-004 — Default deny for unverified integrations and side effects.** GitHub access is limited to the current public repository's read-only metadata/source for this task. Google Cloud, Drive contents, other repositories, owner devices, writes, secret access, paid calls, deployment and merge are out of scope.
5. **ADR-005 — Keep requirements for recovery, service levels and cost configurable and unset.** RTO/RPO, availability, performance and budget cannot be honestly selected without owner objectives, deployment facts and measurements.

These are discovery-stage constraints and proposals, not an approval to implement the full MVI or to access additional resources.

## Prioritized backlog

### P0 — Governance and safe scope

1. Owner reviews/accepts or revises the scope in [`scope.yaml`](../scope.yaml); verify repository permissions, visibility and branch protection through an approved read-only check.
2. Reconcile the existing hosted-backend roadmap with the draft's local-first policy; record the product/provider decision and data-flow constraints in an ADR.
3. Establish data owners, classifications, retention, and secret-scanning/incident response acceptance criteria without disclosing secret values.
4. Establish review and CI acceptance evidence for the actual branch/PR workflow; verify delegated workflow provenance and required checks.

### P1 — Minimum viable inspector prerequisites

1. Define a minimal, explicitly authorized repository-metadata inventory schema and read-only permission set; test pagination, rate limits and redaction before any broader inventory.
2. Design secret finding records that retain only masked evidence, source reference, severity and disposition; run scans only on expressly approved content.
3. Select a local model/runtime only after owner hardware and privacy requirements are measured and the provider-policy conflict is resolved.
4. Specify the smallest task-state, audit, approval and rollback contracts before adding orchestration or external tools.

### P2 — Later capabilities (not Phase 0 authorization)

1. Evaluate storage/RAG, multi-agent orchestration, dashboard, additional integrations, backup and production observability against approved threat model and measured needs.
2. Add local or hybrid inference, sandboxing, resilience and performance only after security tests and owner approval gates exist.
3. Consider automation or write access only with explicit scoped approval, independent review, rollback evidence and fail-closed tests.

## Unknowns and blockers

- Owner operating system, CPU/RAM/GPU/VRAM, disk, network, local runtime and whether a local model can meet requirements.
- Actual repository and user permissions, branch rules, required checks, workflow provenance, private repository inventory and approved integrations.
- Whether OMEGA supersedes the existing hosted-provider roadmap; acceptable prompt egress, provider retention and model licensing.
- Data ownership, classification approval, retention/deletion requirements and permitted inventory sources.
- Budget ceiling, cost approval, latency/throughput goals, availability, RTO/RPO and deployment target.
- Required backup, restore, recovery, audit retention and incident-response procedures.
- Repository license and licensing requirements for future model weights/dependencies.
- Full history and deployment secret status; this task deliberately did not inspect secret values or conduct a comprehensive secret scan.
- Whether/how the Phase 0 result is accepted and the draft PR #19 becomes approved project policy.

## Validation and limitations

Discovery used repository file/path inspection, documentation/code review, GitHub read access to draft PR #19, and read-only runner metadata commands. No code was changed, no external resource was modified, and no production/deployment behavior was tested. The existing test command `python -m pytest -q` was attempted but could not run because pytest is not installed (`No module named pytest`). The proposed scope YAML parsed successfully; CI status was not checked. Phase 0 remains PARTIAL until tests can be run and the unknowns and owner approval gates above are resolved.
