# OMEGA P0 — Runner-host loopback diagnosis and release separation

**Status: not owner acceptance.** This document does not change the PROJECT OMEGA V2.0 100 requirements or broaden network access.

## Observed before this change

- Exact candidate PR #58 commit `f3a812a362428e24aeaa14988bfda52d450df61c`.
- One Compose stack's Docker containers were healthy, internal API/HTTP E2E passed, while the runner-host probe emitted `OMEGA_RUNNER_HOST_LOOPBACK=BLOCKED_NOT_ACCEPTED`.
- The prior probe's observational command exited 0 for this BLOCKED finding, so an otherwise successful E2E job is **not** runner-host reachability evidence.
- No log verified whether the socket was refused, timed out, mapped to localhost, or obstructed by a particular Docker rule. **Root cause was UNKNOWN**.

## New independent evidence protocol

- Existing E2E still reports observations and does not misrepresent a blocked connection as success.
- The dedicated **OMEGA runner-host acceptance (separate P0 gate)** workflow starts its own disposable Compose stack with the original `internal: true` network and `127.0.0.1:18080:8000` published port.
- `scripts/omega_runner_host_diagnostic.py` inspects *only* the Docker-reported mapping (no credentials), confirms all attached networks are internal, verifies API health from inside the container, checks runner-host TCP, then confirms the public mock health and HTTP 403 execution refusal from runner-host if TCP connects.
- The diagnostic prints generic `OMEGA_RUNNER_HOST_*` fields, not IPs other than the fixed expected loopback, Docker IDs, paths, secrets, or exception text.
- The observation step may exit 0 while reporting BLOCKED. The **independent acceptance step** uses `--require-runner-host` and returns 2 on BLOCKED; the dedicated job then fails. A noninternal network or non-loopback publication is UNSAFE and returns 1.
- A failed TCP connection **does not establish its root cause**. Internal network, port publishing, firewall, daemon proxy, or host routing may require separate trusted evidence; do not change the topology just to turn the gate green.

## Owner device procedure — DOCUMENTATION ONLY, NOT EXECUTED

Only the owner, after explicitly choosing the target **local** machine and verifying that it is a disposable OMEGA instance, may perform these read-only checks locally:

1. In the intended project folder, record the local source version and Git commit (if applicable) without copying files or secrets to a public repository.
2. Check that the existing Docker services are already running. **Do not** start, stop, recreate, prune, delete, or migrate any existing service or volume as part of this check.
3. Check the expected compose file *as text* for `internal: true` and `127.0.0.1:18080:8000`. Do not print resolved Compose environment values or container environment.
4. On the owner's own device only, run:
   `curl --noproxy '*' --max-time 5 -sS -i http://127.0.0.1:18080/api/health`
   and check HTTP 200 with `mode=mock` and `production_ready=false`. Optionally use an owner-approved HTTP 403 test for POST `/api/execute`; do not send any real task or secret.
5. Retain only sanitized status and date in the owner's **private** evidence store. If refused, timeouts or an unexpected response occur, record BLOCKED and do not change firewall, network settings or bind to `0.0.0.0`.
6. The owner's device test remains `NOT_RUN` until an actual owner-approved device session has been completed and linked to its **own** source/version.

The CI runner is a different host; its result never proves the owner's device access.

## Separate baselines and no-touch protections

| Source | Scope | Claimed progress | Acceptance |
|---|---|---|---|
| Public GitHub PR #58 | OMEGA V2.0 staged branch | 0 DONE / 21 PARTIAL / 1 BLOCKED / 78 NOT_STARTED (the previously independently reported matrix) | DRAFT / NOT_ACCEPTED |
| Owner-local build 0.1.3 | Independent local code and runtime | 42 complete / 55 partial / 3 unimplemented (previous local audit only) | NOT_VERSION_MATCHED |
| Owner-local build 0.1.2 | Separate older package | UNKNOWN code/hash/runtime match | PRESERVE / NOT_TESTED |

GitHub source and private local source are **not assumed equal**. The private encrypted-backup SHA-256 evidence belongs in an owner-private manifest, not in this public repository. No private source archive, database volume, Drive file, recovery key or credential has been uploaded or modified.

Local 0.1.3 remains separately blocked on deleted-source residual search results; retain independent regression cases for JavaScript symbol loss, embedding OverflowError and dashboard focus loss. No PR #58 pass can close those issues.

No 476/457 account asset, machine, disk, snapshot, subscription or debt result is established here; absent separately authorized read-only access their status is UNKNOWN. No paid resource is to be created.

## Remaining acceptance blockers

Verified identity / scoped permissions; atomic human approval with durable anti-replay controls; authorized GitHub integration; actual local model integration; full secret history scanning and image/dependency CVE review; tested independent restore and key recovery; branch protection and independent human review. All remain open. Do not merge to main or deploy.

## New runner-host evidence (independent gate)

At PR #58 candidate `cffd6a8fcd7e4d33177420a059273d87ac79e87a`,
[GitHub Actions run 38124310806](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38124310806)
job `114425358977` produced:

```text
OMEGA_PORT_POLICY=PASS
OMEGA_RUNNER_HOST_BINDING=MISSING
OMEGA_RUNNER_HOST_NETWORK=INTERNAL
OMEGA_RUNNER_HOST_CONTAINER=PASS
OMEGA_RUNNER_HOST_TCP=REFUSED
OMEGA_RUNNER_HOST_HTTP=BLOCKED
OMEGA_RUNNER_HOST_VERDICT=BLOCKED_NOT_ACCEPTED
exit code 2 (required host acceptance)
```

This proves the **effective Docker-reported publication is missing at the runner** and TCP is refused, while the container and internal network remain healthy. **Why** Docker does not expose the declared localhost mapping remains UNKNOWN; never attribute this conclusively to `internal: true` without a controlled technical cause test. No isolation/bind/security setting has been relaxed. No owner device was contacted. The separate host acceptance workflow's FAILURE is an accurate open blocker, **not** a regression of the independent container-internal PostgreSQL/FastAPI E2E.
