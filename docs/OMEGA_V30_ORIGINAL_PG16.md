# V30 original PostgreSQL 16: exact source replay (not ORBA billing)
The owner-supplied original `OMEGA_V30_POSTGRES_AUDIT_LIVE_HARNESS_297_TESTS.zip`
has SHA-256 `f43211a03a5675e2917202d7403d77bac155af41fb2f726b799baccd47884c3d`.
This draft contains **only 8** original V30 files required to execute the
**original** `tests/test_postgres_live.py` (8) and
`tests/test_postgres_audit_live.py` (8), packaged as compact Brotli tar
(with all extracted bytes independently checked against original manifest).
The rest of the owner's original archive, project documents and evidence
are NOT published. No real user identity, financial data or credentials are used.

CI provisions PostgreSQL 16 in an ephemeral GitHub Actions service. It rejects
any missing dependency, altered source file, skipped test, error, wrong count,
or nonzero exit. The job exercises queue+audit integrity on PostgreSQL, **not**
ORBA Google Play Billing or actual subscription payment flows. Even 16/16 PASS
does **not** prove the exact all-297 tests passed in a single environment;
the user-owned full V30 ZIP is necessary for that. It is already separately
available as a locally validated, offline 281 PASS / 16 SKIP artifact.

This is deliberately a DRAFT PR. No main merge, real payments, production
secrets, merchant setup, live deployment or production acceptance is authorized
by this test-only evidence.

## 11 Nov 2026 exact-source negative test and narrowly scoped candidate

The **actual original V30 16-test PostgreSQL run** on PostgreSQL 16.15
reported **15 pass / 1 error** (run 43100022893). The failing original test
`test_lease_and_completion` used malformed lease token `wrong`: PostgreSQL
rejected the non-UUID value as `InvalidTextRepresentation` before the
application could raise its promised `PermissionError`. This is a **real
pre-existing defect**, not a source acquisition failure or a test skip.

The follow-up test workflow first proves the original byte-perfect source
still fails in **exactly** that way; it then applies a narrow, explicitly
checksum-locked patch ONLY to the ephemeral extracted working copy of
`omega_postgres.py`, validating UUID inputs *before* SQL. The bundled eight
original source bytes, original hashes and historical failure remain unchanged.
A second run requires all 16 tests to PASS with zero skips/errors before
reporting the **patched candidate** as successful. Passing those 16 is NOT
identical to running the entire original V30 297-test suite on the patch,
and does not establish paid monetization or production deployment.
