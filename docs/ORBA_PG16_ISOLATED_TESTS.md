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


## 11 November 2026: PostgreSQL identity and isolation controls

The original 16 synthetic subscription tests remain intact. Four additional
negative tests guard the actual PostgreSQL session identity and the effect
of changing the search_path away from the randomized mock-only schema.
Both read and write operations now deny unless PostgreSQL reports database
omega_mock, role omega_mock, and a strictly formatted omega_mock_<32 hex>
schema. The test harness validates the DSN (local loopback) before connecting
and checks the authenticated role/database before CREATE SCHEMA.

These checks reduce accidental cross-environment execution, but cannot make
this mock module suitable for production billing. Test harnesses still need
an ephemeral instance. CI now requires 20 tests, with 0 skips/errors.
