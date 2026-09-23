# MEHMET AI Backend P1

Server-side bridge for the existing PWA contract.

## Endpoints
- GET /api/health
- GET /api/providers
- GET /api/models
- GET /api/vault/status
- GET /api/owner/status
- POST /api/chat
- POST /api/research (fail-closed until P3)

## Secrets
OPENAI_API_KEY and AI_BACKEND_PROXY_TOKEN must exist only in the deployment environment. Never commit either value.

## Default model
OPENAI_MODEL defaults to gpt-5.6-luna. Allowed models are controlled with OPENAI_ALLOWED_MODELS.

## Security posture
- request body and message caps
- in-memory rate limiting
- provider allowlist
- fail-closed runtime-to-backend proxy authentication for POST /api/chat
- provider errors do not leak response bodies
- no API key in browser/PWA
- research and owner auth remain fail-closed until their dedicated phases

## AI acceptance gate
A healthy container is not sufficient for AI acceptance. POST /api/chat is accepted only when both the private proxy token and OpenAI provider credential are configured. Missing proxy authentication fails closed before any provider call.
