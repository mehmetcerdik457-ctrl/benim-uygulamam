# PROJECT OMEGA S10 — Authorized UI data contract (PROPOSAL / NOT IMPLEMENTED)

This contract describes the **missing live data trust boundary** for OMEGA-072, 073,
074, 077, 078 and 079. It is **not** a production API, authorization grant, identity
provider, permission to query accounts, or evidence of an Android APK.

## Existing implementation — only an isolated demo

Public PR #66 renders fixed offline `/api/demo/inspection` repository metadata
with a filter for repository/folder/service/data source. The only verified fixture
repository is `mehmetcerdik457-ctrl/benim-uygulamam`; all other categories return
an explicitly empty **synthetic-only** result. The view rejects wrong repository
IDs, extra/unexpected fields, negative or noninteger counters and spoofed
`visibility` or description. This does **not** use OAuth, GitHub API, Google
Drive, cloud accounts, search indexes, real user data, or owner-local files.

## Future read-only implementation boundaries — IDP expert must approve

1. A real server-side authenticator (not a caller-supplied `owner` or `role`
   request field) verifies identity, expiry, audience, replay protection and
   any needed MFA. The OIDC module in **draft PR #62** is explicitly a
   synthetic fixture, not a live identity adapter. Until a trusted IdP is
   configured, all **live** data features must return deny/unavailable.
2. Per-request data access is scoped to a server-verified principal, resource,
   action and tenant with least privilege. Never reuse anonymous demo
   permissions for live reads. A UI or Android client is never an authority.
3. Denied, expired, revoked and out-of-scope reads must return uniform
   denial with `Cache-Control: no-store`; no user ID, raw SQL, path, token,
   credential presence, exception text or sensitive metadata may leak.
4. Live inventory results require allowlisted source IDs, source kinds,
   timestamp/freshness, full page bounds and provenance; empty authorized
   result must be distinguishable from unavailable/denied. No unbounded
   enumeration of repos, folders or services.
5. Search results require **post-retrieval ACL enforcement**, per-source
   citation ID verification, current source generation and revocation/deletion
   tombstones; stale citations must not be used after deletion or permission
   removal. UI output uses text nodes only.
6. Secret screen response **must never** include values, auth headers, vault
   payloads or recovery hints; only permitted opaque reference, scope and
   rotation-status metadata. Unauthorized existence checks must not become
   an oracle.
7. PR evidence binds repository, PR number, full 40-hex commit SHA, timestamp
   and check/review/policy status. If SHA moves or checks are unknown, show
   STALE/UNKNOWN, not green. Human approval and CI success are independent.
8. A production API used by either the web panel or separate Android client
   must enforce deny-by-default and rate/size/time limits **on the server**.
   A local authenticated API is allowed if the owner approves its TLS,
   network boundary and endpoint scopes. External no-API providers may use
   owner-directed browser/manual operations; never seize credentials.
9. Browser/Android security: no secret logging, no credentials in URLs,
   no persistent cache by default, CSRF protection for browser sessions,
   correct CORS/origin policy, Android Keystore token storage and forced
   logout/revocation data purge. Access to device/owner machine unverified.
10. Owner and independent inspector must review each bound endpoint,
    negative tenant/ACL/revocation tests, accessibility and exact build
    commit before any acceptance. Do not silently repoint demo endpoints
    or reinterpret fixture SUCCESS as real authorization.

## Explicit negative acceptance checklist

- Missing or forged session, wrong tenant, expired/replayed token, withheld MFA.
- Direct URL access to a resource hidden from client UI, and changed role during
  an open view; server blocks both without leaking existence.
- Partial provider pagination/429, source disappearance, stale cache and
  mismatched citations: distinguish unavailable, denied, tombstoned and empty.
- Secret reference payload containing raw values or unknown fields: reject
  without logging any sensitive value.
- PR check from another SHA, synthetic review mislabeled real, unapproved
  policy decision: reject or display NOT VERIFIED.
- Malformed/null/oversized data, HTML-like strings and cross-origin redirects:
  do not render as trusted links or HTML.
- Android offline refresh / cancellation must not replay privileged actions.

Current S10 UI fixture tests only exercise **synthetic source metadata and
static on-device-independent rendering**. They do not prove any live negative
case above. Original 100 requirements stay untouched; this document is a
handoff for S5 identity, S6 knowledge, S9 GitHub and S12 integration owners.
