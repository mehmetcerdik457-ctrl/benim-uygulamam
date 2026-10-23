# OMEGA CI runner-host gateway, read-only diagnostic and deny-only route

This is an **optional Docker Compose override** for a disposable synthetic demo.
The original PR #58 compose.omega.yml, application, database, original source
blobs, Owner authenticator, local models, and phone artifacts are not changed.

Run only with two Compose files:
  docker compose -f compose.omega.yml -f compose.omega-host.yml up -d --build --wait db api host-gateway
  python3 scripts/omega_host_gateway_acceptance.py

The original API and PostgreSQL database remain on the internal-only isolated_demo
network. The overlay explicitly removes the original API host published port via
Compose !reset [], eliminating a direct bypass. Only a new, nonprivileged gateway
has a host-facing loopback port 127.0.0.1:18081, with a separate dual-network
connection. This is an *intentional limited access path* and introduces a tiny
additional local attack surface. Never enable in production.

Gateway supports ONLY GET /api/health (minimal "mock", not production-ready) and
POST /api/execute (upstream MUST return 403 or gateway fails closed). Other
routes are denied, including /api/chat, /api/models and /api/v1/owner/chat.
Never sends client Authorization/Cookie/Owner headers upstream. No secret logs.
A passing test is "PASS_RUNNER_DEMO_GATEWAY_ONLY_NOT_OWNER", **not** real physical
Owner, local LLM, Android, or production acceptability.

If Compose lacks the !reset syntax, if host port is unavailable, or the gateway
cannot demonstrate both mock health and execution denial on the runner host, the
P0 gate MUST fail. No weakening internal network, no 0.0.0.0 host publish.

This gateway is not a substitute for TLS, enrollment, RBAC, network isolation
review or real Owner phone acceptance. Do not deploy it with actual user data.
