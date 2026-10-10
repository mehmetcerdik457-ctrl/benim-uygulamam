# Phase 0 evidence and acceptance gates

**Status: OPEN; no end-to-end acceptance.** Source: OMEGA v2 1–10 in `docs/PROJECT_OMEGA_MASTER_SPEC_V2.md`; Copilot's separate [PR #21](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/21) is draft and its CI was `action_required` when examined.

| ID | Current evidence | Unmet acceptance gate |
| --- | --- | --- |
| OMEGA-001 | PR21 `docs/PHASE_0_DISCOVERY.md`: tracked files counted, missing license recorded | independent path/license verification and owner-reviewed scope |
| OMEGA-002 | Hosted runner-only measurements documented in PR21 | real owner device measurements: OS CPU RAM GPU VRAM disk network; all UNKNOWN |
| OMEGA-003 | two conflicting draft scope files | owner-approved, enforced single scope and policy tests |
| OMEGA-004 | PR21 P0/P1/P2 list and 100-item matrix on PR22 | owner prioritization and traceable issue acceptance |
| OMEGA-005 | five ADR proposals in PR21 plus ADR-0001/2 in PR22 | alternatives reviewed and decisions formally approved |
| OMEGA-006 | PR21 risk table | adversarial prompt injection, secret, supply chain and abuse tests |
| OMEGA-007 | four classification levels in PR21 | data owner, access control, retention and sample policy tests |
| OMEGA-008 | requirements identified as UNKNOWN | configurable RTO/RPO, latency, availability, cost targets chosen by owner |
| OMEGA-009 | separate dummy-only Compose PR planned/in progress | compose config, build/start, API+Postgres health and regression logs |
| OMEGA-010 | backlog in PR21; architecture + dependency graph in PR22 | approved milestone map, validated diagram and owner signoff |

## Safe default test controls
- A "DONE" status requires exact commit, run/test output, and acceptance evidence. Any missing gate remains PARTIAL/BLOCKED/NOT_STARTED.
- Never scan actual secret file contents. For redaction, use synthetic literal fixtures and test only redacted output.
- GitHub runner CPU/memory are not user's device specifications.
- CI `action_required` with zero jobs is NOT `success`. Require a human to review the Copilot-generated PR and approve the workflow; keep approval protection enabled.
- Use an isolated CI service without real account credentials. Run existing Python regression tests via `python -m pip install pytest` then `python -m pytest -q`.
- `main` public branch and protected-branch settings need read-only verification and owner action; no auto-merge.

Open unknowns: local hardware, GCP, exact authorized integrations, licensing, budget, owner RTO/RPO, secure restore, and real provider approvals.
