# PROJECT OMEGA — PR #58 genuine source-byte import into PR #96

Source commit: `044c558b2b28e05929a9acd79a639a32092ab187` (unchanged blob SHAs under original paths).
Target before integration: `e44274cc5ed873e493fd3baf05c8830c43a25b0b`.

* The 78 imported original files are preserved using their existing Git blob SHA,
  not pasted, reconstructed or generated replacements.
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
