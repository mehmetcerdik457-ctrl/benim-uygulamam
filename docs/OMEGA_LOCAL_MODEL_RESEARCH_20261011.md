# OMEGA MVI — Local model feasibility (research only)

**Status: BLOCKED until verified target-device hardware and owner opt-in.**
No model weights downloaded. No third-party API, GPU or device assumed. Current
`omega_mvi/model_adapter` is deterministic **FAKE**, not real inference.

## Required read-only device profile (owner-controlled)
Capture device OS/architecture, CPU architecture/extensions, available RAM,
GPU vendor/model, VRAM, disk free space, permitted storage directory,
local network binding policy, quantization support, and measured temperature/
power limits. Never confuse GitHub runner specs with owner hardware.
All fields currently **UNKNOWN**. No access to owner device is provisioned.

## Candidate engines (NOT installed)
- `llama.cpp`: cross-platform CPU inference and optional Metal/CUDA/HIP/Vulkan
  backends; quantized GGUF support. Source:
  https://github.com/ggml-org/llama.cpp/blob/master/README.md
- Ollama: possible management wrapper, but installation, daemon and model pull
  must remain explicitly opt-in; not bundled in current Compose.

## Open-weight candidates and provenance (NOT downloaded)
| Model | Size class | Model card | Claimed weight license |
|---|---:|---|---|
| Qwen3-1.7B | 1.7B | https://huggingface.co/Qwen/Qwen3-1.7B | Apache-2.0 |
| Qwen3-4B | 4B | https://huggingface.co/Qwen/Qwen3-4B | Apache-2.0 |
| Granite-3.3-2B-Instruct | 2B | https://huggingface.co/ibm-granite/granite-3.3-2b-instruct | Apache-2.0 |

Licenses are based on official model cards as viewed 2026-10-11; review actual
model revision, tokenizer, weights, redistribution notices and quantization
derivative license at selection time. Quantized distribution can have separate
licenses and untrusted conversion artifacts. Do not automatically fetch models.

## Acceptance protocol (future)
1. Human-scoped, read-only measurements of actual owner device.
2. Model card, hash, dependencies, quantization and license acceptance.
3. Separate non-networked local runtime profile with no secrets/prompts sent
   to external providers; no automatic cloud fallback.
4. CPU/VRAM/RAM and concurrency budgets benchmarked at target context length.
5. Redaction checks, no LLM authority, owner-reviewed sandbox and rollback.
6. Real measured output and CI/local logs; until then model_adapter stays fake.

Research is NOT hardware detection, installation or real inference evidence.
