# OMEGA V34 — Original 354 tests / isolated PostgreSQL CI

Owner-provided source: `OMEGA_V34_ORBA_PLAY_VERIFICATION_354_TESTS.zip`
Original archive SHA-256: `8ccea387dc9e8c7fc9150b0b29244755d1c04b34797a2e19a4f6c4fb93cb1924`.

- The original archive has 62 SHA-256-verified manifest entries; this draft
  stores only 60 original `.py`, `.sql`, and `.yaml` source and test files.
  User metadata, original README, historical logs, and private 100-row
  requirement CSV are intentionally excluded.
- CI reconstitutes every source byte and checks it against the **original**
  file digest catalog before applying any changes. No unverifiable download.
- The unmodified V34 sources produced **338 PASS / 16 SKIP** locally without
  PostgreSQL. They include 8 live queue tests and 8 live audit tests; these
  are **not** ORBA payment or subscription tests.
- The only candidate patch, applied to an ephemeral extracted copy of
  `omega_postgres.py`, translates PostgreSQL SQLSTATE 22P02 for a malformed
  UUID lease token to `PermissionError`, after database rollback, with all
  other DB exceptions re-raised. It does **not** alter original source ZIP.
- The same candidate patch preserved **338 PASS /16 SKIP** locally (no PG).
- CI creates a temporary PostgreSQL 16 container, then a separate database
  `omega_test_v34` owned by a **non-superuser** role `omega_v34` with no
  real credentials. The test code refuses any other DSN and checks the
  authenticated database, user and role privilege before running.
- CI demands exactly **354 tests, zero skipped, zero failed**, in **one**
  PostgreSQL-backed run. A missing PostgreSQL server fails closed, not SKIP.

**What this does NOT establish:** actual Google Play Developer API purchase
verification, a Play Console merchant account, token settlement, genuine
paid entitlements, RTDN/acknowledgement, or live ORBA monetization. V34
`orba_play_bridge.py` accepts a stub provider and tests validate that stub;
there is no server-side authenticated Google Play provider implementation
connected to an authorized ORBA account. No paid or real purchase performed.

Draft integration candidate only. Requires independent code/security review,
account setup, signing/build testing, and separate deployment evidence.
Do not treat CI success as the OMEGA 100/100 requirement acceptance gate.
