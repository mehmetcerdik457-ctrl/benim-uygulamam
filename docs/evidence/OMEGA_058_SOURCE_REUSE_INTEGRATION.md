# PROJECT OMEGA — PR #58 genuine source-byte import into PR #96

Source commit: `044c558b2b28e05929a9acd79a639a32092ab187` (unchanged blob SHAs under original paths).
Target before integration: `e44274cc5ed873e493fd3baf05c8830c43a25b0b`.

* 77 of 78 imported files are original, byte-identical Git blobs;
  the E2E workflow is intentionally adapted to install both dependency sets.
* Existing stdlib backend, Owner authenticator and PR #93 recovery verifier
  remain separate from the isolated `omega_mvi/` demo.
* No automatic model or provider execution; Owner verification and approval
  remain unimplemented/denied.
* The old PR #58 requirement CSV is a historical tracker, not an adopted DONE
  acceptance matrix. PR #93 legacy 0.1.4/0.1.5 archive bytes are not recovered.
* Tests run on disposable CI PostgreSQL, synthetic-only inspectors and local
  HTTP. Host loopback blockage, real owner device and real deployment are
  acceptance blockers, **even if CI succeeds**.
* `main` remains unchanged; merge requires explicit approval and independent
  review. Actual source file refs: Git commit `044c558b2b28e05929a9acd79a639a32092ab187`.

## Git readback
At integration HEAD `4389b61c2a4a2cdee903501cde67d2f77cd83cae`, 77 files were confirmed byte-for-byte identical
(by original Git blob identity) to `044c558b2b28e05929a9acd79a639a32092ab187`, one intentionally changed workflow.
Machine-readable manifest `docs/evidence/OMEGA_058_SOURCE_GIT_BLOBS.json`
is regression-checked by `scripts/omega_verify_reused_mvi.py`.
This is a Git identity check, **not** a SHA-256-signed release attestation,
nor proof of private 0.1.4-dev or 0.1.5 archive recovery.

A separate strict P0 CI job will check runner-host loopback and **fail**
when blocked; routine container/DB E2E success must not imply host acceptance.
