# OMEGA target architecture and dependency milestones

**Conceptual MVI design only**: this diagram is not a deployed system.

```mermaid
flowchart TD
  Owner[Owner browser] --> UI[Turkish dashboard]
  UI --> API[Isolated FastAPI control plane]
  API --> POLICY{Default-deny policy and human approval}
  POLICY --> TASKS[Task state machine and audit]
  TASKS --> PG[(PostgreSQL metadata)]
  TASKS --> MODEL[Local LLM adapter with mock fallback]
  TASKS --> INVENTORY[Read-only GitHub adapter]
  TASKS --> RAG[Redacted source-cited retrieval]
  TASKS --> REVIEW[PR risk and CI evidence reviewer]
  RAG --> PG
  REVIEW --> POLICY
```

## Delivery dependency graph
```mermaid
flowchart LR
  P0[Phase 0 scope and regression] --> M1[1 Compose FastAPI health]
  M1 --> M2[2 PostgreSQL schema and migration]
  M2 --> M3[3 state machine and audit]
  M3 --> M4[4 deny policy and approval]
  M4 --> M5[5 local adapter and mock tests]
  M4 --> M6[6 scoped inventory]
  M6 --> M7[7 redaction and sourced retrieval]
  M4 --> M8[8 independent PR reviewer]
  M3 --> M9[9 Turkish dashboard]
  M5 --> M10[10 integration security restore]
  M7 --> M10
  M8 --> M10
  M9 --> M10
```

## Milestones
- P0A: agreed narrow scope, owner device UNKNOWN until measured, existing roadmap preserved.
- P0B: 100-row requirement matrix, ADRs, threat/data classification tests and accountable approvals.
- P0C: dummy-only Compose and FastAPI health without real secrets, with reproducible tests.
- MVI-A: DB and state+audit/policy tests.
- MVI-B: mock model + read-only GitHub + redacted RAG + PR reviewer.
- MVI-C: Turkish UI, full CI gates and restore rehearsal with non-sensitive dummy data.
- Later: remaining 100-step requirements after validated MVI, separately authorized integrations and hardware measurements.

## Recovery design (not a backup)
Backups must be encrypted *on the client* before Drive upload; key managed separately in an approved secret store. Attach manifest of file names, versions, non-sensitive provenance and SHA-256 hashes (ciphertext integrity) plus signed/authenticated encryption metadata. Perform restore on a clean sandbox with dummy data, validate hashes and usability, document RTO/RPO. No private upload or backup-success claim until encryption, owner approval and restore tests are passed.
