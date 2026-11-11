# ORBA: disposable PostgreSQL mock ledger (16 NEW tests)

**Not an ORBA production billing system. No money is received or moved.**

These 16 real PostgreSQL integration tests cover a mock-only ledger:
schema, purchase, pending, exact replay, conflicting replay, refund, expiry,
cancellation (mock semantics only), renewal, owner isolation, wrong owner,
real purchase label rejection, SQL injection defense, live mode refusal,
transaction rollback and cross-owner event collision.

The previous V30 artifact was described as 281 passed + 16 skipped = 297,
but the actual V30 package is NOT accessible in the connected repository,
Drive or local working environment here. Therefore these are 16 DISTINCT
tests and must NEVER be called the former 16 unskipped V30 tests.
No Play Billing SDK, purchase token verification, Google Play Developer API,
ORBA merchant account, AdMob, RTDN, settlement, revenue or deployment exists
in this mock. No real payment credentials are used.

GitHub Actions starts an ephemeral PostgreSQL 16 CI service and enforces
16 tests / zero skips. Missing database is FAILURE, not a pass or skip.
Every test creates/drops its own random schema; never run on a live DB.
Run locally only with isolated PostgreSQL and environment variable
OMEGA_ORBA_MOCK_PG_DSN, with psycopg[binary] installed.

To implement real subscriptions, separately verify the authorized Google
Play Console application/package and merchant, use a currently supported
Billing Library version (8 or newer for current new releases), validate
each purchase token server-side with the Google Play Developer API, never
grant entitlement for PENDING, implement acknowledgement and RTDN,
refund/revocation/grace handling, idempotent server processing, audit
events, privacy/security controls and license-tester evidence.

Do not merge/publish without independent owner/security review and a
production acceptance process. This file does not override PROJECT OMEGA's
deny-by-default release controls.
