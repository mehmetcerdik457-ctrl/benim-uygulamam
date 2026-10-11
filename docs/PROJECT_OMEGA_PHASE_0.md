# PROJECT OMEGA — Phase 0 Baseline

Updated: 2026-10-11

This document records repository discovery and design constraints before
expanding the implementation. The only machine measured was the isolated task
runner; its resources are **not** evidence about the owner's computer or a
deployment target. See [`../scope.yaml`](../scope.yaml) for observed details
and explicit authorization boundaries.

## Repository inventory

| Area | Current contents | Status |
| --- | --- | --- |
| Backend | `backend/server.py`, Python standard library HTTP server | Exists; not FastAPI |
| Tests | `tests/test_backend_contract.py`, placeholder test | Small contract suite |
| Dependencies | `requirements.txt` states stdlib-only | No application packages pinned |
| Configuration | `.env.example` | Placeholders; includes external provider configuration |
| CI | GitHub workflows, including a reusable Python baseline | Present; branch protections not verified |
| Security | `SECURITY.md`, privacy guard workflow | Present |
| Documentation | `AI_MASTER_ROADMAP.md`, `CURRENT_STATE.md`, backend README | Existing roadmap differs from PROJECT OMEGA target |
| License | No license file found | Licensing terms are unknown |
| Runtime services | No Compose, database, local model, UI, or queue configuration found | Not implemented |

The existing chat backend sends submitted messages to OpenAI when configured.
It is not local-first and must not be presented as the OMEGA local model
adapter. No secret value was inspected. Hardware probes observed only the
task-runner environment; no owner directories, disks, or external accounts
were inspected.

## Scope and authorization

`scope.yaml` is the machine-readable boundary for this work. The current scope
is limited to this public repository checkout. Availability of `gh` or Docker
executables does not establish authentication, permission, or a configured
service. GitHub account/API access, owner hardware, cloud projects, Drive
folders, provider credentials, and deployment targets remain unverified or
unprovisioned. Unknown authorization is denied, not inferred.

## Requirement priorities

### P0 — safe, testable MVI foundation

- Local-first operation and privacy-by-default; no confidential data sent to a
  cloud model by default.
- Explicit scope and least-privilege authorization; deny unknown permissions.
- Secrets are references only outside the secret store and are excluded from
  model context, logs, Git, reports, and indexes.
- Read-only/dry-run defaults; human approval before destructive or external
  actions.
- Honest capability, hardware, integration, and test status.
- Auditable task lifecycle, bounded execution, cancellation, and failure
  reporting.
- Local development environment, health checks, tests, and install
  documentation before claiming readiness.
- MVI core: task state machine, local model adapter, authorized read-only
  GitHub inventory, secret redaction, source-cited retrieval, PR review report,
  approval policy, and Turkish management UI.

### P1 — important after the safe core

- PostgreSQL-backed canonical metadata, permission-filtered indexing, hybrid
  retrieval, provenance, incremental updates, and backup/restore.
- GitHub PR/CI integration, policy checks, stronger identity and audit
  controls, observability, and operating procedures.
- Additional model profiles, evaluation and resource measurements on actual
  supported hardware.

### P2 — advanced, gated capabilities

- Multi-agent execution, multiple GPUs/providers, graph retrieval, automated
  remediation, production operations, and expanded cloud integrations.
- Any autonomous write, merge, deploy, device action, or broad filesystem
  operation. These require separate authorization, isolation, tests, and
  explicit human approval; they are not part of the initial MVI.

## Architecture baseline

```text
Turkish Web UI
     | authenticated, versioned API
     v
FastAPI control plane ---- policy + human approval
     |                         |
     +-- task state/audit -----+
     +-- authorized GitHub read-only adapter
     +-- secret scan/redaction (values never persisted)
     +-- local model adapter (network disabled by default)
     +-- retrieval API with ACL filtering and source citations
               |
         PostgreSQL metadata
         local vector/index store (selection benchmark-gated)
```

Trust boundaries:

1. Browser input, repository content, PRs, model output, and tool output are
   untrusted.
2. The policy/approval layer—not model output—decides whether an operation is
   permitted.
3. Secrets are isolated from the database, retrieval index, prompts, and logs.
4. Provider and GitHub adapters receive narrow, task-specific capabilities;
   no broad credential catalogue is exposed to agents.
5. External or destructive operations remain disabled unless separately
   approved and verified.

### Dependency and trust graph

```text
Web UI -> FastAPI API -> policy/approval -> task coordinator
                                   |            |
                                   |            +-> local model adapter
                                   |            +-> GitHub read-only adapter
                                   |            +-> retrieval service -> PostgreSQL
                                   +-> audit events (redacted metadata only)
Secret store -> narrowly authorized adapter at call time only
```

PostgreSQL is the proposed canonical metadata store. The vector store,
secret-store implementation, authentication provider, model/runtime, and
container isolation mechanism are unselected pending target-hardware and
threat-model validation. Do not add a runtime dependency or claim a selected
provider until those decisions are benchmarked and reviewed.

## Data classification

| Class | Examples | Handling |
| --- | --- | --- |
| `public` | Public repository files and public metadata | Index only within authorized repository scope; cite source |
| `internal` | Task plans, non-public operational metadata, audit event metadata | Access-control filtering; minimize retention and log fields |
| `confidential` | Private source, user documents, account/resource metadata | Explicit source authorization; local processing; never expose across ACLs |
| `restricted` | Tokens, passwords, private keys, recovery codes, raw secret matches | Never store in Git, prompts, logs, reports, or RAG; redact and retain references only |

Classification follows the most sensitive content in a record. Secret scanners
may report a masked finding with provider, path, risk, and status; they must not
persist the matched value.

## Threat model

| Threat | Risk | Initial controls / remaining work |
| --- | --- | --- |
| Secret leakage into prompts, logs, Git, or RAG | Credential compromise and data exposure | Redact before indexing/context creation; secret scanning; tests for log and output leakage; revoke via official provider flow only |
| Prompt injection in repository, PR, or tool output | Unauthorized tool use or data exfiltration | Treat all external content as untrusted; separate policy from planner; tool allowlists, egress controls, approval gates |
| Supply-chain compromise | Malicious dependency, image, or CI action | Pin and review dependencies/actions; scan dependencies and images; generate SBOM before release |
| Privilege escalation or confused deputy | Agent uses broader authority than task requires | Per-tool identities and scopes; deny by default; enforce authorization outside the model; short-lived credentials |
| Malicious PR or compromised contributor | Code execution, secret theft, policy bypass | Isolated CI; least-privilege tokens; required checks and human review; no merge authority for reviewer agent |
| Unauthorized repository or filesystem discovery | Privacy/ownership violation | Scope allowlist; explicit user authorization; no automatic whole-machine scans |
| Model hallucination or unsafe recommendation | Incorrect action or false assurance | Never treat model decisions as permissions; source citations, deterministic verification, explicit uncertainty |
| Service or model failure | False success, duplicate action, uncontrolled retry | Explicit failure states, deadlines, bounded retries, idempotency, cancellation and audit trail |

Residual risks remain until the corresponding controls are implemented and
tested; this baseline is not a security certification.

## Operational objectives and unknowns

RTO, RPO, availability, latency, throughput, budget, retention, and model
quality targets are unknown. They must be configured per deployment and
measured; no default target is asserted here. The initial local development
profile should have no external network access except integrations explicitly
enabled for a test. Production use is out of scope until backup/restore,
security gates, authorization, and acceptance tests exist.

## Milestones and initial backlog

1. **Governance and design (current):** scope, inventory, priorities, threat
   model, classifications, ADR, architecture, and unknowns.
2. **Local foundation:** Compose profile, `.env.example`, Makefile, health
   checks, FastAPI app, PostgreSQL migration, and CI tests.
3. **Safe task core:** versioned task schema/state machine, bounded queue,
   cancellation, audit metadata, approval policy, and negative authorization
   tests.
4. **Local AI and data access:** local model adapter selected against actual
   hardware; authorized read-only GitHub inventory; secret masking; ACL-aware
   source-cited retrieval.
5. **Review and UI:** PR review report, Turkish UI, approval/stop controls,
   documented setup and recovery.
6. **Acceptance:** adversarial security tests, backup/restore validation,
   integration tests, capability/status review; do not claim production-ready
   unless all required gates pass.

Each milestone is gated on test evidence. The current repository does not yet
meet the MVI acceptance criteria.
