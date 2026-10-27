# OMEGA specialist 10 — Turkish dashboard, source integrity, Android APK boundary

Status: **DRAFT / NOT ACCEPTED / NO DEPLOYMENT**. Parent baseline: public PR #58 HEAD
`044c558b2b28e05929a9acd79a639a32092ab187`.
This specialist branch changes only the **public GitHub demo source-reference guard** and
adds isolated regression tests. It does not assert that the private owner-local 0.1.4-dev
Chromium focus patch was inspected or changed. No credentials, user DB, or private backup
was read. Original OMEGA V2.0 requirements 1–100 remain authoritative and unmodified.

## Evidence classification

- **REAL**: a response directly observed from an explicitly authorized system,
  attributable to the checked full commit SHA, actor/scope, timestamp, and request.
- **SYNTHETIC**: disposable fixed fixtures, mock local-model responses, or local
  test database aggregate counts. Never label as real owner GitHub, RAG, billing, or PR status.
- **UNKNOWN / DENIED / STALE**: never coerce into success or empty "healthy" data;
  deny privileged interactions and show a clear Turkish status.

## Original numbered acceptance boundaries

| Item | Public GitHub baseline | Remaining required evidence |
| --- | --- | --- |
| 72 | PARTIAL: synthetic health, four offline inspectors and disposable PG aggregate status counts | Real owner-authorized service/model/queue observations, billing/cost source, error and freshness alerts, scoped read-only runtime |
| 73 | NOT_STARTED: no filterable repo/folder/service/data-source inventory UI | Backend ACL per record, filter/pagination, forbidden source denial, revoked-source removal and mobile tests |
| 74 | NOT_STARTED: no authenticated semantic search screen. SyntheticRetriever uses immutable fixtures, owner string check and source refs | Source-to-corpus binding, verified citations and ACL, wrong source test, deleted-document/tombstone test with real index lifecycle and cache invalidation |
| 77 | NOT_STARTED: no secret management metadata UI | Reference ID, allowed scopes and rotation state only. Never emit secret value, credential existence oracle, vault payload, recovery material or raw audit |
| 78 | NOT_STARTED: offline advisory PR review only, no authoritative PR UI | Exact 40-char full SHA from GitHub, per-SHA check runs, policy and signed human review, timestamp/provenance, stale and synthetic labels, no approval inferred from CI |
| 79 | NOT_STARTED: no real IdP, MFA, sessions or backend RBAC | Owner-approved identity scheme, server-side least privilege, tenant isolation, MFA where needed, session expiry/revocation, CSRF/cookie settings, audit, negative privilege tests |
| 80 | PARTIAL visual baseline: Turkish, viewport meta, dark stylesheet and focus-visible button; not full acceptance | English localization, TalkBack/screen reader, WCAG 2.2 AA contrast and focus, 320/390/768 responsive, touch targets, reduced motion, light-theme support, Android device tests |

The previous CSV matrix is not changed here; acceptance ownership rests with the
central coordination issue and chief inspector.

## Concrete specialist evidence

1. Previous PR #58 strict CSP uses same-origin JS/CSS and DOM textContent, with
   POST /api/chat and /api/execute returning 403; live PG tests target a
   **disposable CI database**, not owner data.
2. Isolated browser test of copied public panel assets (headless Chromium,
   in-memory mocked fetch, **not real host network**) passed 320px, 390px and
   1280px layout, Tab/Enter focus retention on refresh, dark stylesheet, denied
   API, and unsafe external URL handling. The forged source
   `synthetic://<img...>` was displayed as inert text by the original
   script (XSS blocked; provenance check FAILED).
3. New JS guard accepts only the three *fixed synthetic fixture references*, valid
   integer scores, at most five unique refs, and explicit synthetic-only response
   mode. It fails closed on forged synthetic prefixes without accepting any real
   external source. A separate authenticated schema is required before production.
4. New in-repo Node VM and pytest tests exercise known/forged/external/duplicate/
   malformed references and synthetic owner mismatch. They are not equivalent to
   live tenant/corpus/deleted-source tests.
5. Isolated Chromium rerun after the fix: all six responsive/source cases passed.
   Browser test harness does not prove network exposure, native APK, screen reader,
   owner-local Chromium 0.1.4-dev, or production authorization.
6. PR #58 exact base SHA has 7 successful workflows and one failed *separate*
   runner-host acceptance; internal container API PASS does not prove host access.

## Android APK: separate extension requirements (not claims about original 100)

- **APK-A01**: Create a separate Android client using Kotlin/Jetpack Compose or
  another owner-approved maintained native stack; reuse the existing FastAPI
  backend. Do NOT rewrite the backend as part of the APK.
- **APK-A02**: Include health, tasks, inventory, cited search, secret **metadata**
  and PR evidence screens only after each corresponding backend authorization
  contract exists; unsupported functions show unavailable/denied.
- **APK-A03**: Support a configured owner-controlled **local API** over an
  authenticated, encrypted connection; do not assume local APIs are forbidden.
  No wildcard port exposure or unapproved private-network traversal.
- **APK-A04**: For external services with **no API**, provide secure browser
  hand-off/manual import with explicit owner consent, never covert screen scraping,
  session hijacking or credential extraction. State the automation limits.
- **APK-A05**: Use OIDC Authorization Code + PKCE in trusted external browser
  where approved, backend-enforced RBAC/MFA/session revocation; keep tokens in
  Android Keystore-backed storage and never in logs, URL query or screenshots.
- **APK-A06**: Deny mutations by default. Show target, scope, diff, risk, expiry
  and rollback; require server-verified fresh human approval. Offline mode does
  not queue destructive actions for silent replay.
- **APK-A07**: Restrict cached private data, redact logs, clear/revoke upon logout
  and ACL or document deletion, and avoid secret values in notifications.
- **APK-A08**: Test TalkBack, large fonts, 320dp+ adaptive layouts, keyboard,
  screen readers, dark/light themes, offline/timeout/error states and focus
  preservation on supported Android versions and actual devices.
- **APK-A09**: CI produces an installable versioned signed APK and provenance
  (full commit SHA, app/package ID, build variant, artifact SHA-256, SBOM,
  supply chain scans); signing material stays owner-private.
- **APK-A10**: Verify on a disposable Android emulator and an owner-approved
  Android handset; demonstrate exact installed APK talks to explicitly authorized
  OMEGA backend without bypassing identity or increasing service privileges.
- **APK-A11**: Keep private local **0.1.4-dev** Chromium focus issue separate:
  inspect its real code and tests read-only before deciding if any fix should be
  ported. Public PR tests cannot establish equivalence.

## Release gates

No release/DONE unless authenticated scoped real data, source deletion and ACL
revocation, secure secret metadata, exact-SHA PR evidence, identity/MFA, complete
keyboard/mobile accessibility, owner-device and Android E2E, independent review,
owner approval, and secure signed APK are individually proven. No live credentials
are required from the user for the synthetic tests here.
