# PROJECT OMEGA — scoped knowledge controls (033, 038, 039, 040, 089)

**Status: EXPERIMENTAL / synthetic fixtures only / NOT ACCEPTED.** This proposal is stacked on PR #58 head at `044c558b2b28e05929a9acd79a639a32092ab187`, and must not be confused with the separate private `0.1.4-dev` commit `053e75d5591c836714d27d2d8b9b3f74c4464b9f`. The original 100-step specification remains authoritative.

## Scope and changes

- **033**: `omega_mvi/inspection/knowledge/code_graph.py` uses Python AST to list definitions, imports, calls and callback candidates. Name binding is unresolved; attribute/dynamic dispatch remains `unknown`. JS/TS scanning is strictly heuristic, NOT a reliable parser or runtime call graph; tests inspect two existing public repo files.
- **038**: `benchmark.py` plus `scripts/omega_knowledge_fixture_benchmark.py` expose recall@k, nDCG@k, local Python wall-time p50/p95, and traced Python heap. Bundled candidates are only lexical token-overlap and exact phrase search on three synthetic documents. **Neither is an embedding or reranker model.** Real embedding/reranker comparisons are `SKIP_NOT_INSTALLED` pending owner-approved offline weights, pinned revisions, hardware, representative corpus, measured RSS/CPU/VRAM and actual model runs. The GitHub runner is not the owner device.
- **039**: `ControlledIndex` stores only explicitly allowlisted `synthetic://` source fixtures in process memory. Tombstones stop a deleted document ID or the same content with a new identity for that source. Source revocation blocks search, **new** context and reindexing; linked memory is checked on every read. An `RLock` serializes lifecycle, search and trust reads to avoid observed scan/revoke races. `context_snapshot` and `assert_context_current` provide a consumer-side stale-generation check, but cannot retract previously delivered text.
- **040**: Controlled, approval-flagged and allowlist-scoped incremental `rescan` (never interprets omitted documents as deleted) and explicit complete-source `replace_source_snapshot`. A complete fixture snapshot atomically tombstones removed IDs and source-scoped content hashes; same-content rename in that source is denied, cross-source injection is rejected and malformed batches leave old data intact. Changes increment a monotonic generation. No filesystem watcher, webhook or persistent source-of-truth connector is enabled.
- **089**: `MemoryLedger` moves entries from `unverified_suggestion` to `approved_fact` and then `tested_solution`; trust escalation requires explicit evidence-reference and approver metadata. Unverified suggestions never enter trusted context. Referenced source revocation excludes all its memories.

## Non-negotiable boundaries

**Logical filtering is NOT physical deletion, backup cleanup, persistent vector removal or retroactive erasure from earlier LLM prompts.** There is no persistent index here. A previously issued context string cannot be withdrawn. No production data, personal account, token, key, branch merge, deployment or paid model is touched.

Identity strings and `approved=True` are dummy-only test flags, not real authentication or cryptographic authorization. Memory evidence IDs are synthetic metadata only, not verified test logs. The content redactor is heuristic and can miss sensitive information. Real ACL sync, persistent idempotent tombstones, distributed cache propagation/TTL, concurrent readers outside this Python process, source lifecycle/restore/reindex semantics, backup retention, cryptographic erasure, verified approver identity, independent test evidence and separate training consent remain **BLOCKED**. The in-process generation check is advisory until every downstream context consumer enforces it immediately before use. A fresh independent source can legitimately contain the same content; this does not claim global erasure.

The user-reported private `0.1.4-dev` deleted-source regression fix was **not accessed or reimplemented**. Its existing tests must be independently read and run before acceptance. No production records were deleted.

## Reproduction

From the repository root:

```bash
python -m compileall -q omega_mvi/inspection/knowledge scripts/omega_knowledge_fixture_benchmark.py tests/test_omega_knowledge.py
PYTHONPATH=.:omega_mvi python -m pytest -q tests/test_omega_knowledge.py
PYTHONPATH=.:omega_mvi python scripts/omega_knowledge_fixture_benchmark.py
PYTHONPATH=.:omega_mvi python -m pytest -q
```

Tests are scoped to offline fixtures. The benchmark prints honest `SKIP_NOT_INSTALLED` for real embedding/reranker candidates. Invalid duplicated rankings, rankings exceeding top-k, and unstable repeated rankings are rejected rather than reported as valid quality scores. Timing numbers reflect the machine on which the command is actually run; Python traced allocations are NOT RSS or VRAM.

## Remaining acceptance gates

| Item | Remaining blocker |
|---|---|
| 033 | Syntax-aware JS/TS parser and real module/type resolution; dynamic-path unknowns validated against wider corpus |
| 038 | Real pinned embedding/reranker candidates, relevant evaluation data and owner-device RAM/VRAM/CPU/quality/latency numbers |
| 039 | Existing private fix/regressions; live IdP/ACL; persistent search/vector/cache invalidation; restore/backup/race checks |
| 040 | Durable incremental checkpoints; on-disk and external source change feed; rename/move/delete, watcher and restart tests |
| 089 | Verified human approvals, immutable evidence review, retention controls and independent training consent |

**Rollback:** Close draft PR or revert the new knowledge package, benchmark script, tests and this file. No migrations, identities, secrets, model router, GitHub inventory or other experts' modules are modified. Merge and production acceptance require independent review plus explicit owner authorization.

## Second-pass regression extensions (exact SHA required for acceptance)

Additional automated tests exercise complete snapshot omission, same-content renamed documents, atomic rollback of invalid batches, empty snapshot behavior, explicit approval requirement, generation-stale context after revoke, scoped cross-source duplicate content, a controlled threaded scan/revoke sequence, memory context after a full-source deletion, invalid duplicate/oversized/unstable benchmark rankings and the executable offline benchmark CLI. Passing these tests establishes **fixture-only** behavior, not that actual vector stores, caches, backups or prompt histories are cleaned. CI evidence must be read from the GitHub Actions run for this PR's **final** commit SHA; earlier CI runs do not qualify.
