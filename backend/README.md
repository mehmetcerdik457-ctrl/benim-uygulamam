# MEHMET AI Backend P2

Server-side model router for the existing MEHMET PWA contract.

## Endpoints
- GET /api/health
- GET /api/providers
- GET /api/models
- GET /api/vault/status
- GET /api/owner/status
- POST /api/chat
- POST /api/research (fail-closed until its provider is configured)

## Providers

### OpenAI
Profiles:
- `max` → `gpt-6-astra`
- `balanced` → `gpt-6-sol`
- `fast` → `gpt-6-luna`

The allowlist also preserves the existing GPT-5.6 Sol/Terra/Luna models for compatibility.

Required secret:
- `OPENAI_API_KEY`

### Hugging Face / open-source
The router uses Hugging Face's OpenAI-compatible Inference Providers endpoint.

Profiles:
- `max` → `deepseek-ai/DeepSeek-R1:preferred`
- `balanced` → `openai/gpt-oss-20b:preferred`
- `fast` → `Qwen/Qwen3-8B:preferred`

Required secret:
- `HF_TOKEN`

The exact model allowlists and profile mappings are environment-configurable. No provider secret is committed to source.

## Chat request

```json
{
  "message": "Merhaba",
  "provider": "openai",
  "profile": "max"
}
```

Optional `model` can select a specific model only when it is present in that provider's allowlist.

## Security posture
- private PWA-runtime → backend proxy token required for chat
- provider credentials remain server-side
- explicit provider/model allowlists
- body/message caps
- in-memory rate limiting
- provider errors do not leak response bodies
- missing credentials fail closed
- no automatic cross-provider fallback that could hide errors or cause surprise spend
- owner auth and research remain separately fail-closed until their dedicated gates

## Acceptance gate
Container health alone is not AI acceptance.

For an OpenAI runtime PASS:
1. `AI_BACKEND_PROXY_TOKEN` configured on runtime/backend
2. `OPENAI_API_KEY` configured server-side
3. one real `gpt-6-astra`/approved model response
4. response provider/model receipt captured without secret leakage

For an open-source runtime PASS:
1. `HF_TOKEN` configured server-side with required inference permission
2. one allowed open-source model response through Hugging Face Inference Providers
3. response provider/model receipt captured
