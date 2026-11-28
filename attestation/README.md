# OMEGA Attestation Evidence Inventory

**Status: NOT PRODUCTION ACCEPTED.** This inventory is documentation of observed evidence and gaps. It is not a deployment receipt, device proof, cryptographic approval, or production authorization.

## Observed PR #105 state

- PR: https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/105
- Head branch: `audit/omega-deployment-attestation-plan-20261111`
- Observed head commit: `f21dbdcb3c9d61f72379338090bee7c3ad0adf4b`
- PR state: open, draft, not merged
- CI run: PASS
- Privacy Guard run: PASS
- OMEGA Deployment Preflight Tests run: PASS
- These checks validate the structural preflight and regression tests only.

## Evidence matrix

| Evidence | State | What is actually available | Required next step |
|---|---|---|---|
| Exact source commit | PARTIAL | PR head SHA above | Bind release tag and immutable build provenance to this exact SHA |
| Real signed release artifact | MISSING | No APK/AAB or production artifact attached to #105 | Build in protected release workflow; record artifact SHA-256 and signature certificate |
| Owner cryptographic signature | MISSING | Test fixtures generate ephemeral keys only | Sign exact artifact digest using independently provisioned owner key; store public key fingerprint |
| Independent auditor signature | MISSING | No trusted auditor key or signature | Obtain independent auditor key and signature over the same canonical receipt |
| CI logs | PARTIAL | Three PR-triggered checks passed | Export complete run/job logs and bind their SHA-256 to evidence manifest |
| Device smoke evidence | MISSING | No physical-device run or device identifier supplied | Run install, launch, critical flows, network/privacy checks on a real target device; save timestamped logs |
| Deployment receipt | MISSING | No authenticated deployment ID/environment receipt | Deploy only to approved staging; export authenticated receipt with commit, artifact digest, actor, timestamp |
| Rollback proof | MISSING | No rollback receipt or rehearsal log | Perform staging rollback rehearsal; record prior/new deployment IDs and smoke results |
| Billing proof | MISSING | No real end-to-end Play Billing evidence | Use Play test environment; test purchase, restore, cancel, expiry, refund and RTDN replay |
| 100-item acceptance | BLOCKED | PR #101 states 100 BLOCKED / 0 VERIFIED | Collect original requirement-specific receipts and independently verify each |

## Safe commands for evidence generation

Run from a clean checkout at the exact release commit:

```bash
git rev-parse HEAD
git status --porcelain
./gradlew --no-daemon clean :app:assembleRelease :app:bundleRelease
sha256sum app/build/outputs/apk/release/*.apk app/build/outputs/bundle/release/*.aab
apksigner verify --verbose --print-certs app/build/outputs/apk/release/*.apk
jarsigner -verify -verbose -certs app/build/outputs/bundle/release/*.aab
```

For a connected Android test device:

```bash
adb devices -l
adb install -r app/build/outputs/apk/release/<verified-release.apk>
adb shell am force-stop <application.package>
adb shell monkey -p <application.package> 1
adb logcat -d -t 5000 > device-smoke.log
sha256sum device-smoke.log
```

Replace placeholders only after confirming the actual package name and artifact path. These commands have not been run against a physical device in this audit.

## Admission rule

A green CI run or a valid test fixture is not production acceptance. Keep `production_accepted=false` until artifact provenance, distinct trusted signatures, real device evidence, deployment receipt, rollback, billing, and every mandatory requirement are independently verified.
