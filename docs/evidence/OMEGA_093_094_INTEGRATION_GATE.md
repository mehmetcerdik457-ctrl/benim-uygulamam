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
