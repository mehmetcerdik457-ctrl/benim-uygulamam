# P1 backend pre-deploy diagnostics

The existing Railway deployment failed during `PRE_DEPLOY_COMMAND`; its returned
build log finishes with an image push and its pre-deploy log is unavailable.
The exact old failing predicate is not established.

`python scripts/predeploy_gate.py` replaces the opaque compound pre-deploy
command with named, redacted results. It still requires source compilation,
the existing `scripts/security_selftest.py`, the fixed Responses API endpoint,
nonempty provider/proxy/owner-key configuration, a selected model and a positive
integer output-token limit. Invalid numeric environment values are reported by
field name before they can leak through an import traceback.

The command prints only fixed check names/statuses and the existing
`OMEGA_PREDEPLOY_OFFLINE` marker. It never prints values, exception messages or
subprocess output. Exit 0 requires every check to pass; failures or unrun checks
exit 2. There is no skip flag. No provider request is made and no variables or
owner keys are changed.

This is a configuration/self-test gate, not a live model acceptance test. The
owner-key check preserves the existing nonempty-value contract; it does not
establish enrollment, a valid public key, device possession or owner consent.

After a reviewed source commit is connected, Railway can use:

- pre-deploy command: `python scripts/predeploy_gate.py`
- pre-deploy timeout: 180 seconds
- start command: `python backend/server.py`
- healthcheck: `/api/health` (120 seconds)

The start command, selected model and existing provider/proxy/owner variables
must be preserved. A passing gate is followed by separate HTTP health and
bounded, authorized real-provider acceptance tests.
