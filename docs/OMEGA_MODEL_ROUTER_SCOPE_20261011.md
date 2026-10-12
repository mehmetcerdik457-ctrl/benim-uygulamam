# PROJECT OMEGA — Sohbet 7 / Local model routing evidence

**Scope:** Original Master Engineering Specification v2 requirements **41, 44, 47, 48, 49, 50**. This is an **isolated, unconnected prototype** and optional read-only probes. It does **not** enable `/api/chat`, start or download models, contact paid providers, modify production routes, or prove owner-local inference.

## Version and trust boundaries

- Public GitHub integration: PR #58 branch at the audited parent commit `044c558b2b28e05929a9acd79a639a32092ab187`, **not** `main`. Existing `omega_mvi/model_adapter/testing.py` is deterministic fake-only and `/api/chat` remains HTTP 403.
- Private 0.1.4-dev Qwen3 operation is **reported, not accessed or verified**. Owner hardware, model hash/tag, execution trace, tokenizer, resource measurements and actual inference metrics are all UNKNOWN.
- Agent's isolated execution container results are **NOT owner hardware**; never accept CI worker or assistant container data as owner-machine evidence.
- No GPU/VM/disk was provisioned, no weights downloaded, no API keys or owner documents accessed.

## Six-requirement acceptance ledger

| ID | Work in this draft branch | Remaining blocker |
|---|---|---|
| 41 | `scripts/omega_local_hardware_probe.py` runs passive CPU, RAM/cgroup and optional NVIDIA query in the executing environment | Owner device CPU/GPU/VRAM and supported profile still UNKNOWN |
| 44 | Official Qwen3 1.7B, Qwen3 4B and Granite 3.3 2B cards identify Apache-2.0 weights | Exact revision, derivative weights/hash/license, Turkish/code quality and owner's RAM/VRAM suitability NOT TESTED |
| 47 | `model_adapter/router.py`: task, privacy, quality, latency, token/context and external-cost allowlist | Only fake tokenizer/backend exercised; actual local adapter and measured quality values missing |
| 48 | Async timeout, per-model and global concurrency semaphore, cancellation, bounded retry, token/identity checks; negative fixture tests | Real runtime cancellation and OS-level memory/VRAM/resource limits missing |
| 49 | `scripts/omega_loopback_model_benchmark.py` supports *existing* Ollama at numeric localhost with three public synthetic TR/EN/code smoke cases; safe metric-only output | No actual target-device model accessed. Real TTFT/tokens/s, peak RAM/VRAM, cost and robust task success NOT MEASURED |
| 50 | Transient failures retry and select another policy-eligible local model; permanent and usage-violation failures halt; no auto cloud fallback | Live crash/OOM/process restart and real fallback E2E NOT TESTED |

None of these six items is DONE. Do not confuse synthetic router fixture outcomes with model benchmark outcomes.

## Safety and functional constraints

1. Default global inference concurrency **1**; catalogue count (including 10–50 registered entries) does **not** mean the same number of large loaded/running models. No implicit remote backend or nonzero external spend.
2. `quality_by_task` and `measured_p95_latency_ms` are caller-supplied **metadata**. Production usage requires evidence; tests assign **synthetic fixture values**, not independently measured quality. If request requires p95 and no measurement exists, deny.
3. Backend tokenizer must count exact prompt **including system/chat-template tokens** before scheduling. Fixture uses word counting, not a production tokenizer; therefore actual provider token budgets are NOT validated. Backend must enforce output-token max independently; response usage is checked post hoc.
4. Provider cancellation is **cooperative**. A detached process/thread could continue after timeout. Real runtime must demonstrate kill/cleanup, bounded queues, safety after OOM and resource release.
5. All fallback candidates are screened against task, privacy, verified quality, latency, cost, allowed model and token/context constraints. Unknown errors are sanitized and fail closed, not logged with prompts.
6. Local inference benchmark only requests existing tagged model on 127.0.0.1; it neither pulls models nor calls arbitrary hosts. No model answers printed. The three smoke questions are deliberately too small to support global model quality claims.
7. Existing app endpoints, CI workflow and private files are untouched.

## Independent reproduction

```sh
PYTHONPATH=. python -m pytest -q tests/test_omega_model_router.py tests/test_omega_local_hardware_probe.py tests/test_omega_loopback_model_benchmark.py
python scripts/omega_local_hardware_probe.py
# ONLY on the owner's explicitly selected machine with Ollama already running:
python scripts/omega_loopback_model_benchmark.py --model EXISTING_LOCAL_MODEL_TAG
```

If no localhost runtime is accessible, smoke script emits `NOT_MEASURED` and exits **2**, rather than inventing benchmark data.

For acceptance, record real owner-environment CPU/RAM/GPU, available VRAM, context length, model identifier/revision/checksum/license, tokenizer hash, run command and dependency versions, warmup/cold run isolation, n and distribution (p50/p95 TTFT/total latency), eval tokens/s, peak VRAM/RAM, bilingual task success by rubric, power/cost where measured, fallback and crash traces, timeouts and rollback. Never publish private machine identifiers, secret-bearing prompts or full local file manifests.

**Rollback:** revert this separate draft PR only. Keep existing PR #58 and main unchanged. Final merge/enablement requires independent review, successful exact-SHA CI and explicit owner decision.

## Second audit hardening (2026-10-12; same DRAFT PR #68)

This supplement is **additional code/testing**, not owner-local inference acceptance:

- `ModelRouter(..., max_inflight_requests=8)` now limits **admitted + queued** requests per router instance, refusing overload before executing a backend; the default running concurrency stays 1. Cancellation releases admission. This implementation is **single-asyncio-event-loop only** and is NOT a machine-wide or multi-worker capacity coordinator.
- Strict enum/int/quality checks reject malformed privacy metadata, bool-as-int values, invalid task quality and model cost values. Registered quality metadata is copied so a mutable caller dictionary cannot silently downgrade routing after registration.
- A backend that suppresses cooperative cancellation and returns **after an attempt timeout** cannot have its late result accepted or fallback continued. This is an output safety gate, **not** proof that the backend was killed on deadline: an uncooperative subprocess/runtime could continue consuming RAM/GPU. Production needs an isolated, killable worker and real timeout/OOM E2E tests.
- Local smoke script now performs `GET http://127.0.0.1:<selected-port>/api/tags` and requires an **exact already-installed** Ollama model name before any POST inference. No auto-pull, install or remote lookup. Invalid/missing catalogue returns `NOT_MEASURED` and exit 2. A successful opt-in generation still **uses computation** and can load already-installed weights into memory; do **not** describe it as a read-only resource-neutral operation.
- New offline negative suites `tests/test_omega_router_hardening.py` (34 cases) and `tests/test_omega_ollama_preflight.py` (6 cases) use mocks; no owner model was run. The 34 router-hardening cases were observed PASS in an isolated assistant Python test container; GitHub Actions results must be checked against the final PR HEAD separately.
- Original text says test path `tests/test_omega_model_router.py` as an initial suite. The complete focused command now includes both newly added test files, too:

```sh
PYTHONPATH=. python -m pytest -q \
  tests/test_omega_model_router.py \
  tests/test_omega_router_global_limit.py \
  tests/test_omega_router_hardening.py \
  tests/test_omega_ollama_preflight.py \
  tests/test_omega_local_hardware_probe.py \
  tests/test_omega_loopback_model_benchmark.py
```

### Still NOT accepted
No real Qwen3 measured latency/TTFT/tokens/s, model weights digest on owner machine, robust TR/EN/code quality, VRAM/RAM, multi-model failover or crash/OOM/cancellation worker cleanup evidence. The synchronous injected tokenizer itself must be verified as bounded (router event-loop deadline cannot interrupt a blocking synchronous tokenizer call). Existing `/api/chat` is disabled. Do **not** advance item 41/44/47/48/49/50 to DONE.
