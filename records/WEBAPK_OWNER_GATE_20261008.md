# MEHMET PWA v0.2.2 — Android WebAPK Owner Login Acceptance, 2026-10-08

## Canonical identity / source (evidence)
- Uploaded `base.apk` and `DOC-20261008-WA0004.apk` are identical: 125,465 bytes;
  SHA-256 `2662b4c64a132e4ac628baa71318755faf3c586d583e93841458df8b511fc9c1`.
- Manifest package: `org.chromium.webapk.ac2060520de884095_v2`.
- Manifest start URL: `https://mehmet-pwa-v022-runtime-production.up.railway.app/MEHMET.html`.
- This is a Chrome WebAPK shell; AI engine and web interface live on the HTTPS origin, not in the APK.
- Original release ZIP recovered from Google Drive and verified:
  `MEHMET_YARATILIS_PWA_v0.2.2.zip`, size 164333,
  SHA-256 `518d82cceb2843bc4db75d46876f1adc57558b601264bf2e888c9b09232fcbb0`.

## Current production behavior (OBSERVED)
- Runtime service `mehmet-pwa-v022-runtime` serves pinned Git commit
  `089164a1feba48268278c72f8765aa1ba3ac9758`.
- 2026-10-08 Railway HTTP readback: `/MEHMET.html` and `/sw.js` returned 401 repeatedly.
- Code uses HTTP Basic owner authorization from environment variables
  `OWNER_BASIC_USER` and `OWNER_BASIC_PASSWORD` before serving protected assets.
- Therefore the Android credential dialog is expected when the user has not
  provided the correct owner credentials. Password and username values MUST NOT
  be exposed in GitHub, chat, logs, or client-side JavaScript.
- New backend pre-deploy was blocked after OpenAI provider HTTP 429; historical
  provider diagnostic identified `insufficient_quota`. A successful real model
  response is NOT VERIFIED.

## New offline regression gate (this commit)
`scripts/owner_acceptance.py` tests the actual WebAPK entrypoint, root entrypoint,
manifest, JavaScript, and service-worker assets: anonymous requests must return
401; requests authenticated with synthetic test owner credentials must return
HTTP 200 with nonempty bytes. Also tests anonymous `/owner-login` returns 401.
Existing positive/negative owner API checks and mock chat remain in place.

## Separate unresolved gates
1. Physical Android owner login: NOT_VERIFIED (requires user to enter their
   existing owner credentials in the device's protected authentication dialog).
2. Real AI model reply: BLOCKED/NOT_VERIFIED (provider 429; billing/rate reason
   needs safe provider-side verification).
3. Physical installation, camera, microphone, TTS, encrypted storage, offline
   close/reopen and end-to-end persistence: NOT_VERIFIED.
4. Model vision/audio ingestion is absent: current PWA forwards attachment
   metadata and SHA-256 but not binary content to a multimodal inference adapter.
5. Model-router PR #17 and Sites BFF PR #18 remain DRAFT/UNMERGED.
6. Phone MCP plugin `mehmet-android-mcp` is NOT_INSTALLED in current session;
   no connected Remote Desktop device was available.

## Release and permission boundaries
- No production deployment, credentials rotation, user data clearing, app
  uninstall, APK repack/resign, or PR merge is performed by this test commit.
- Do not weaken HTTP Basic authorization to make the startup prompt disappear.
- This regression is not a physical-phone PASS and is not paid-model inference.
