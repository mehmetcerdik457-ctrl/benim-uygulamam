# OMEGA Owner v1 — integration candidate (NOT PRODUCTION ACCEPTED)

Source: public MEHMET AI backend PR #87 HEAD bdfbb7822bf83a9b8543930e982a0f029cc416e6. This branch adds a **new route**, it does not merge Android code, FastAPI, D1–D5 or signed APKs.

## Running code path
POST /api/v1/owner/chat: exact body and route are signed twice using P-256 ECDSA with SHA-256; a registered Owner identity key and registered device identity key must both verify. Fresh timestamp (30 seconds) and durable SQLite nonce table enforce replay resistance before any OpenAI call.

Separate server-provisioned, pinned public DER key values are required:
OMEGA_OWNER_ID, OMEGA_DEVICE_ID, OMEGA_OWNER_PUBLIC_DER_B64, OMEGA_DEVICE_PUBLIC_DER_B64, OMEGA_NONCE_DB.
Without them the new route returns 503 OWNER_IDENTITY_NOT_PROVISIONED. This is **not an enrollment endpoint** and does not assert a real user's identity until the public keys have been independently verified and approved.

Request headers: X-Omega-Owner-Id, X-Omega-Device-Id, X-Omega-Timestamp (10-digit Unix seconds), X-Omega-Nonce (32–64 lowercase hexadecimal digits), X-Omega-Owner-Proof and X-Omega-Device-Proof (unpadded base64url P-256 DER-encoded ECDSA signatures).

Signature message UTF-8 bytes:
OMEGA-OWNER-API-V1 + LF + POST + LF + /api/v1/owner/chat + LF + sha256(exact JSON request body) + LF + timestamp + LF + nonce + LF + owner id + LF + device id.

Body: {"message":"Merhaba","provider":"openai","attachments":[]}.
Response on a successful _synthetic_ upstream: {"text":"...","model":"...","provider":"openai","request_id":"...","contract":"OMEGA-OWNER-API-V1"}.
Errors are fixed: OWNER_IDENTITY_NOT_PROVISIONED, OWNER_AUTH_REQUIRED, OWNER_AUTH_EXPIRED, OWNER_IDENTITY_DENIED, OWNER_AUTH_DENIED, OWNER_AUTH_REPLAY_OR_STORAGE_DENIED, OWNER_AUTH_STORE_UNAVAILABLE; no secret echo.

## Acceptance boundaries
- Model call takes existing server-side OPENAI_API_KEY; never transfer Owner Android Keystore API key or private material to this server.
- A simulated signed-client HTTP test validates real cryptographic verification and provider adapter invoked with a synthetic fake response. It is **not a real Android Keystore** test.
- No real Android owner enrollment, owner private key issuance, signed APK update, physical phone test, independent production identity audit, real OpenAI live response or FastAPI/PostgreSQL integration is yet proven.
- The original /api/chat PWA route continues under its original policy and must not be considered an Owner-authorized action endpoint.
- Persistent nonce SQLite file must reside on a filesystem surviving restarts, with restricted write permissions; never replace this with an in-memory cache.
- Do not expose local-only Compose service beyond 127.0.0.1 without approved TLS termination, reverse-proxy authentication and independent review.
- No shell/phone action is authorized by /api/v1/owner/chat; no privilege escalation is exposed.

## Integration hold — Owner authority remains unprovisioned
The source-level `owner_execution_authorized()` returns `False` unconditionally.
**Neither valid test signatures, environment flags nor an API key authorize egress.**
All HTTP provider routes (`/api/chat`, `/api/models`, `/api/v1/owner/chat`)
and direct adapter functions deny before a network request without independently
reviewed Owner enrollment. Tests explicitly monkeypatch the deny function for
simulated provider coverage; this is not a deployable enrollment mechanism.
Do not replace the deny function with a config toggle or accept this PR as Owner enrollment.

## Separately restored MVI code is NOT an Owner egress grant
The recovered `omega_mvi/` FastAPI demo from PR #58 uses a different HTTP
server, mocks all identities and denies operations. It must not use the Owner
v1 proof as an approval token or bypass the fixed-false backend runtime policy.

### Updated signed device ID validation (PR #94, 23 Oct 2026)
The request envelope requires an Owner ID matching `[A-Za-z0-9_-]{1,64}` and a device identifier matching `[a-f0-9]{64}`. A matching configured string alone is NOT enrollment. The runtime provider-execution gate stays disabled. Tests use a synthetic 64-character digest only.

### Android device public-key binding (23 October 2026)
The Android TrustedDeviceManager.deviceId() returns hex SHA-256 of the device
Keystore public-key SubjectPublicKeyInfo DER. OMEGA now requires the asserted
device identifier to equal SHA-256(pinned device DER) and rejects using the same
public key for both Owner and Device. This closes a real wire-identity
misconfiguration gap without activating any provider call or enrolling anyone.
The Python wire-vector test directly matches Gpt-asistan Java test source
commit `639ac11db15ea658992c5b91b9c33c1a767902f6`;
the physical Android device, signing key and release remain unverified.
