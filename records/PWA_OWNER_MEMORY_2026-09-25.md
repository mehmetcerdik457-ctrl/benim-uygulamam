# MEHMET PWA owner login and memory update

Target: existing runtime-forensic-v022 Railway service and origin.

Code: ae6c1c1a2194caf3e369f02ea388f9800af8cb1a.

Changes: existing server-side Basic owner gate is provisioned through Railway environment variables; no secrets in source. UTF-8 credentials compare safely. Owner status is generated only after runtime authentication. Original ZIP preserved with versioned app.js/sw.js overrides. Same IndexedDB name/version and origin are preserved. Memory is sent to the model only after a new explicit opt-in checkbox, and memory-enabled setting must also remain enabled. Recent conversation context is limited to the current session. No browser storage is cleared.

Local checks passed: Python compile, JS syntax, runtime_security_selftest, HTTP owner gate (mock backend), wrong-password rejection, unauthed chat/report denial, memory context opt-in, session isolation, context length bounds. Synthetic fresh JavaScript runtime tests are not physical phone/IndexedDB evidence.

Deployment-time --live acceptance sends one synthetic model prompt through an authenticated runtime and checks actual provider output. Real-provider outcome must be read from Railway deployment logs; this source record alone is not PASS evidence. Restore ordinary pre-deploy checks after the one-time live acceptance.

Not implemented: registered-device binding, passkey/MFA, full OWNER_MAX, global third-party product ownership, cross-device memory sync, Internet research. Existing phone memory must not be reset.
