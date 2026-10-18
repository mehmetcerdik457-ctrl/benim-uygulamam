# PROJECT OMEGA — Phase 0 Account & Hardware Inventory (Masked)

Updated: 2026-11-21
Source: read-only GitHub REST reads with the task-runner token; no secret values
were read, stored, or printed. Everything not directly verified is marked
`UNVERIFIED`, never inferred as granted. See [`../scope.yaml`](../scope.yaml)
for the authorization boundary and [`PROJECT_OMEGA_PHASE_0.md`](PROJECT_OMEGA_PHASE_0.md)
for the baseline plan and threat model.

## 1. Repository inventory (20 visible repositories, all public)

| # | Repository | Own/Fork | Primary language | License | Workflows | Last push | Notes |
| - | ---------- | -------- | ---------------- | ------- | --------- | --------- | ----- |
| 1 | `Gpt-asistan` | own | Python | none | 2 | 2026-11-20 | KRAL/Android + assistant base; active front (draft PRs #116–#120) |
| 2 | `benim-uygulamam` | own | Python | none | 3 | 2026-11-17 | OMEGA control plane; active front (draft PRs #101, #105) |
| 3 | `.github` | own | Python | none | 10 | 2026-10-26 | Profile/organization defaults |
| 4 | `skills` | fork | Shell | Apache-2.0 | — | 2026-10-19 | Cloudflare skills (upstream license) |
| 5 | `rish-mcp` | fork | Go | MIT | — | 2026-10-05 | Android shell MCP control |
| 6 | `apk-starter` | own | — | none | 1 | 2026-09-30 | APK build starter template |
| 7 | `docs` | fork | TypeScript | MIT | — | 2026-09-26 | Railway documentation |
| 8 | `studio` | own | Shell | none | 1 | 2026-09-21 | Repo generation / automation scripts |
| 9 | `termux-mods` | own | — | none | 1 | 2026-09-21 | Termux config collection |
| 10 | `bot-starter` | own | — | none | 1 | 2026-09-21 | Bot starter template |
| 11 | `openai-agents-python` | fork | Python | MIT | — | 2026-09-21 | Multi-agent framework |
| 12 | `doktor` | own | — | none | 1 | 2026-09-21 | Error analysis / diagnostics |
| 13 | `repo-template` | own | — | none | 1 | 2026-09-21 | Repo template |
| 14 | `serverless-starter` | own | — | none | 1 | 2026-09-21 | Serverless starter template |
| 15 | `hata-ayiklayici` | own | — | none | 1 | 2026-09-21 | Debugger / log helpers |
| 16 | `codespaces-react` | fork | JavaScript | MIT | — | 2026-09-19 | Codespaces template |
| 17 | `telefon-yedek` | own | — | none | 1 | 2026-09-19 | Phone backup |
| 18 | `mehmetcerdik457-ctrl` | own | Python | none | 2 | 2026-09-19 | Profile repository |
| 19 | `Magisk` | fork | Kotlin | GPL-3.0 | — | 2025-08-29 | Magic Mask for Android |
| 20 | `Shizuku` | fork | Kotlin | Apache-2.0 | — | 2025-06-18 | Android privilege framework |

Observations:
- No private repositories were found with the connected token; absence of
  private repos is a token-visibility observation, not a proof that none exist.
- 7 of 13 own repositories carry no license file. Decision required (P0 backlog).
- 3 repositories (`benim-uygulamam`, `.github`, `Gpt-asistan`) host the active
  OMEGA/KRAL engineering work.

## 2. Token / account permission inventory (observed 2026-11-21)

| Capability | Result | Interpretation |
| ---------- | ------ | -------------- |
| Read public repo contents | OK | Read scope present |
| `permissions` on `benim-uygulamam` | `admin/maintain/push` reported | Declared on this endpoint; actual write ability separately confirmed only where a write succeeded |
| Issue/PR comment write (REST + GraphQL) | **HTTP 403** `Resource not accessible by integration` | Deny-inferred: token lacks issue/PR comment write |
| Branch protection read (`/branches/main/protection`) | **HTTP 403** | Deny-inferred: token cannot read protection state; roadmap still records `MAIN_BRANCH_PROTECTION = OFF` (UNVERIFIED) |
| Google Cloud / Drive / provider access | not provisioned (per `scope.yaml`) | Deny-inferred, unchanged |
| Real device / owner hardware | never accessed | Out of scope until owner-verified |

Rule applied: unknown authorization is denied, not inferred (`unknown_permissions_are_denied: true`).

## 3. Hardware verification plan (to be executed on the owner's machine)

Each item must produce an evidence artifact (log/Screenshot hash) before any
status may move from UNVERIFIED. The task-runner's specs (in `scope.yaml`) are
NOT evidence about the owner's machine.

| # | Item | Probe (read-only) | Evidence expected |
| - | ---- | ----------------- | ----------------- |
| H1 | OS + version | `uname -a`, `cat /etc/os-release` | Command output file |
| H2 | CPU/RAM/GPU | `lscpu`, `free -h`, `nvidia-smi`/`rocm-smi` | Command output file |
| H3 | Disk capacity for DB + model weights | `lsblk`, `df -h` | Command output file |
| H4 | Docker/Compose + `gh` auth states | `docker version`, `gh auth status` | Redacted statuses only |
| H5 | Python + Android SDK/JDK versions | `python3 --version`, `java -version`, `sdkmanager --list` | Command output file |
| H6 | Android device + hardware-backed keystore (StrongBox/TEE) | adb enumeration; Play Integrity/Keystore attestation | Attestation result hash |
| H7 | Biometric/device-credential gate | Device setting check via app diagnostics | Test log |
| H8 | Network egress posture | Local egress matrix run | Egress test log |

Exit criterion: all items have evidence artifacts with timestamps and hashes;
anything not verifiable stays UNVERIFIED and blocks phase advancement claims.

## 4. Remaining access gaps and evidence links

| # | Gap | Status | Evidence |
| - | --- | ------ | -------- |
| G1 | Production acceptance gate (OMEGA-001..100 all `BLOCKED` by design) | Open, deny-by-default | [PR #101](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/101) |
| G2 | Deployment attestation preflight (exact-head CI now SUCCESS) | Awaiting independent review | [PR #105](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/105); runs [#44158746514](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/44158746514), [#44158745306](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/44158745306) |
| G3 | Token cannot comment / read branch protection (403) | Open until token scopes are reviewed by owner | Section 2 above |
| G4 | Branch protection on `main` | UNVERIFIED; roadmap records OFF | [PR #101](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/101) contract; owner must verify |
| G5 | Google Cloud / Drive / provider provisioning | Not provisioned; metadata-only checks BLOCKED | [YAP-24](https://linear.app/mehmetcerdik457gmailcom/issue/YAP-24/omega-cloud-476-metadata-only-access-check-blocked), [YAP-25](https://linear.app/mehmetcerdik457gmailcom/issue/YAP-25/omega-cloud-457-metadata-only-access-check-blocked) |
| G6 | Real device runtime tests (Android owner root, StrongBox/biometric) | Unverified | [YAP-9](https://linear.app/mehmetcerdik457gmailcom/issue/YAP-9/p14p15-blocker-android-owner-root-device-runtime-gate), [YAP-11](https://linear.app/mehmetcerdik457gmailcom/issue/YAP-11/p35-android-device-strongboxbiometric-runtime-gate) |
| G7 | License decision for own repos lacking one | Open (7 repos) | Section 1 |
| G8 | Repo visibility decision (public vs. move product code private) | Open | `AI_MASTER_ROADMAP.md` Phase 0 item 3 |

Coordination record: [Issue #25](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/issues/25).
