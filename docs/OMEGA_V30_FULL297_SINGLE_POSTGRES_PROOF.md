# Exact source V30: one complete 297-test PostgreSQL candidate run

This is a development test-only workflow, NOT a payment/merchant release.

The original user's V30 ZIP SHA-256 was:
f43211a03a5675e2917202d7403d77bac155af41fb2f726b799baccd47884c3d

To avoid publishing unrelated private archive evidence, this draft contains
only 53 original V30 Python, SQL and fixture sources required for the 297
tests. They were independently checked byte-for-byte against the original
ZIP manifest. The source-only Brotli tar SHA-256 is:
348318d4bf8591cb0135ab7d1bb2f63eaa6ac6466f494579649f5ca2c6e0093d

The workflow reconstructs only those files, checks the archive SHA, validates
all seven chunks, applies the narrow, checksum-locked PostgreSQL UUID error
fix ONLY to the extracted test working copy and runs all 297 cases in one
ephemeral PostgreSQL 16 session with a non-superuser account. The original
source archive remains unchanged. This is distinct from PR #102's 20 NEW
mock-ledger tests.

Exact 297 cases, 0 SKIP, 0 FAIL, 0 ERROR, and exit code zero are all required
to emit V30_PATCHED_FULL_297=297_PASS_0_SKIP. Errors fail closed.

Passing means only the patched V30 test suite passed this one configuration;
no ORBA Google Play Billing API integration, verified purchase receipt,
merchant payout, production deployment, 100-point feature acceptance or
independent human review is implied. Do not merge/release on this result.
