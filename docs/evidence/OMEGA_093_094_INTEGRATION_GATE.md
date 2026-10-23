# OMEGA #93 + #94 isolated integration gate

- Source #93: commit `83dd8c6210b49d966107bc1c423f0ce6496d7ab5`, three files imported without byte edits.
- Source #94: commit `18a24c822c0a3763118796d3824773118e28b060`, nine changed files originally reviewed.
- This integration is stacked on #94 only; #93 and #94 remain separate DRAFT PRs.
- Zero Owner enrollment, zero authorized egress. HTTP and direct adapter paths
  deny provider calls by default. Synthetic test fixtures are not enrollment.
- Provenance verifier is read-only and does not claim historical bytes are present.
- The public `main` branch and private 0.1.4-dev/D4/D5 source are untouched.
- CI PASS is a code quality gate, not proof of original 100-item acceptance.
- Required next steps: independent Owner enrollment, test on real device, signed
  Android client validation, original archive bytes, production network/backup
  and full cross-module E2E.

- Second-pass provenance hardening: unsafe symlink paths count as `files_unsafe`;
  all manifest entries and source_version are validated before reading archive bytes.

- Further regression import: model allowlist strict selection from PR #91 HEAD
  `78d216a04b769f622387b5987a13ec9ef8307c7b`, and untrusted
  HTTP peer/log tests from PR #90 HEAD `5e736393fa1d1534b5e01ef436a9925acf2b628e`.
  These are code/test transfers, not claims that PR #90/#91 are merged.

## 23 October 2026 — PR #94 reconciliation
- PR #94 advanced to `d94e406c8a334f6c6255865d3119e81f90b2e068` (two commits from original `18a24c8`).
- This reconciliation incorporates the exact Owner ID/device digest format validation from PR #94 and adjusts the existing synthetic Owner tests.
- Parentage of this merge commit includes PR #96's previous HEAD `3f9a78f02eae60574c524988929afcca667aa1ab` and the current PR #94 HEAD `d94e406c8a334f6c6255865d3119e81f90b2e068`, retaining both histories without force pushes.
- Owner execution policy remains default-deny. No Android device enrollment or real owner approval has been implemented.
