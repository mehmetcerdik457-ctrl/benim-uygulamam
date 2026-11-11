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
