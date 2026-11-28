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
OPENAI_API_KEY must exist only in the deployment environment. Never commit it.

## Default model
OPENAI_MODEL defaults to gpt-5.6-luna. Allowed models are controlled with OPENAI_ALLOWED_MODELS.

## Security posture
- request body and message caps
- in-memory rate limiting
- provider allowlist
- provider errors do not leak response bodies
- no API key in browser/PWA
- research and owner auth remain fail-closed until their dedicated phases

## Runtime contract check
Run `python -m pytest -q tests/test_compose_health.py` from the repository root
to verify the health and legacy GET contracts against the backend in isolated
Docker Compose. The fixture publishes its ephemeral host port only on
`127.0.0.1` and uses an internal Docker network. Do not treat this contract as
accepted until the test has passed on a real CI runner with Docker Compose.
