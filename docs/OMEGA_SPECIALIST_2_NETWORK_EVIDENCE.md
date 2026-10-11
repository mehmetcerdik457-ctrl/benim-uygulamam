# OMEGA — runner-host port publication audit (Specialist 2)

Scope: existing GitHub PR #58 only; this is a stacked draft. Never owner-local 0.1.4-dev or owner device acceptance. Original V2.0 requirements are unchanged.

## Fixed baseline evidence (11 Oct 2026)

- PR #58 initial HEAD: \`044c558b2b28e05929a9acd79a639a32092ab187\`
- Source: https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38124421525
- Job: \`114425698956\`
- Compose requested \`127.0.0.1:18080:8000\`, \`isolated_demo.internal: true\`; policy PASS.
- GitHub runner observed: API container healthy and internal HTTP PASS; \`NetworkSettings.Ports\` mapping MISSING; network INTERNAL; TCP REFUSED; host HTTP BLOCKED.
- \`--require-runner-host\` exited 2; the independent job correctly ended FAILURE. No HTTP 200 or HTTP 403 was obtained **from the runner host**.

These observations prove the *immediate failure*, namely no effective host publication. They do **not**, by themselves, determine the Docker engine's internal reason why the requested publication was omitted. This signature also appears in Moby discussion #53256: https://github.com/moby/moby/discussions/53256 ; external reports are not substitutes for this project's run-specific evidence.

## New read-only CI audit

\`scripts/omega_runner_host_port_audit.py\` obtains:

1. Sanitized Docker server version (digits/dots/hyphen only).
2. \`docker inspect --format '{{json .HostConfig.PortBindings}}'\` — requested runtime mapping.
3. \`docker inspect --format '{{json .NetworkSettings.Ports}}'\` — effective mapping.
4. \`docker compose -f compose.omega.yml port api 8000\` — effective Compose port observation.
5. \`docker inspect ... NetworkSettings.Networks\` and each \`docker network inspect ... .Internal\` — ALL networks must be internal.

Only bounded status codes are logged. The tool does not print Docker IDs, raw JSON, environment variables, passwords or diagnostics from exceptions.

- Exit 0: expected loopback mapping verified in all Docker views, but **HTTP and owner-device status are still unverified**.
- Exit 1: wildcard/nonloopback/extra port or noninternal network \`UNSAFE\`.
- Exit 2: requested publication not active, missing container or incomplete evidence \`BLOCKED_NOT_ACCEPTED\`.

The workflow still runs the independent TCP/HTTP/HTTP-403 enforcement; the acceptance gate **stays FAILURE** while host connectivity is blocked. No override or \`continue-on-error\` has been added.

Eight deterministic tests cover negative and positive audit classification; these are simulated Docker responses, **not** real Docker networking evidence. Real runner observations must come from the new workflow job.

## Security boundary and corrective options

Do not change \`internal: true\`, publish to \`0.0.0.0\`, enable Docker host networking, add an unfiltered second network to the OMEGA API, weaken firewall rules, or claim an internal-container health check proves runner-host connectivity. Docker Compose documents that an internal network has no default external gateway. Introducing an ordinary second network grants the attached service an additional egress path and cannot be silently treated as an equivalent security policy.

To make local UI access a release requirement, the Chief Inspector must approve a separately threat-modeled loopback-only ingress design **and** independent egress-denial tests before modifying the topology. Until then the host acceptance gate should remain red. No production deployment or main merge is permitted.

Owner-machine checks require a separately approved session and independent code/version binding. Private local 0.1.4-dev, disks, encrypted Drive backups, DBs and recovery keys were not inspected or changed.
