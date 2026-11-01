# MEHMET AI Backend P1

Server-side bridge for the existing PWA contract.

## Endpoints
- GET /api/health
- GET /api/providers
- GET /api/models
- GET /api/vault/status
- GET /api/owner/status
- POST /api/chat
- POST /api/v1/owner/chat (proxy token plus enrolled P-256 owner signature)
- POST /api/research (fail-closed until P3)

## Secrets
OPENAI_API_KEY and AI_BACKEND_PROXY_TOKEN must exist only in the deployment environment. Never commit either value.

## Default model
OPENAI_MODEL defaults to the full gpt-4.1 model. Set it to another model supported by your OpenAI API project when desired. There is no application model allowlist; the old OPENAI_ALLOWED_MODELS variable is ignored. The configured model is sent exactly as selected, without a fallback to a different model or provider.

GET /api/models reports the configured default, selection_restricted=false and automatic_fallback=false. A model appearing in the provider's catalog does not prove available billing quota.

An insufficient_quota or billing_hard_limit_reached response returns HTTP 429 with PROVIDER_QUOTA_EXHAUSTED and the explicit instruction “Hesaba bakiye yükle”. Check API credit and organization/project spend limits. The backend does not retry on a cheaper model.

## KRAL guide adapter

runKralAiTask accepts userMessage and requestId, sends the owner's guide's exact trusted system prompt and metadata.request_id to the Responses API, and returns text/model/responseId. The existing HTTP routes call this adapter; their server-generated request_id is preserved and responseId is the actual provider response ID. The existing output cap, store:false policy and attachment-metadata boundary remain unchanged.

An upstream 401 maps to OPENAI_ACCESS_DENIED; upstream 403/404 maps to OPENAI_MODEL_NOT_AVAILABLE. These are provider failures, distinct from the gateway's own owner/proxy authentication failures. Quota errors retain the explicit quota instruction without fallback.

The adapter does not advertise tools or execute model/user-supplied tool requests. Adding real side-effect capabilities requires a separate backend-owned registry and verified approval mechanism; a prompt alone is not permission to execute actions. Client-supplied system prompts, tools and approval fields are not copied into provider configuration.

## Security posture
- request body and message caps
- in-memory rate limiting
- provider allowlist
- fail-closed runtime-to-backend proxy authentication for POST /api/chat
- provider errors do not leak response bodies
- no API key in browser/PWA
- research remains fail-closed until its dedicated phase; owner chat requires its enrolled P-256 key and the proxy token

## AI acceptance gate
A healthy container is not sufficient for AI acceptance. POST /api/chat is accepted only when both the private proxy token and OpenAI provider credential are configured. Missing proxy authentication fails closed before any provider call.

