# PROJECT OMEGA: independent 100-requirement acceptance gate

Status: **NOT PRODUCTION ACCEPTED.** This is an acceptance-control contribution, not the implementation of the original 100 requirements.

The `evidence/omega-100-acceptance.json` manifest has exactly `OMEGA-001` through `OMEGA-100`. All entries are explicitly `BLOCKED` with reasons until evidence is reviewed. The authoritative requirements remain in the owner's master specification; this public repository does not receive private evidence, secret values, model weights, or user data.

The offline CLI validates the full ID set and per-record state. `BLOCKED` is an explicit negative verdict, not a fabricated success. `VERIFIED` entries require an exact source commit, a bounded locally readable test log matching its SHA-256, an exact run ID, observed device/platform, owner acceptance and two independently signed receipts (auditor and owner). Their separate Ed25519 public keys must be supplied from trusted sources with `--trusted-pubkey` and `--owner-pubkey`; no public or private keys are shipped in the repository. The signature binds requirement ID and the complete proof metadata. **SHA-256 alone is integrity, not signer identity.** A cryptographic signature alone does not prove the test actually ran: reviewers must audit the log, source, device/deployment receipt and chain of custody before signing. Never sign metadata merely to obtain PASS.

```
PYTHONPATH=. python -m unittest discover -s tests -p 'test_omega_acceptance_gate.py' -v
python scripts/omega_acceptance_gate.py --manifest evidence/omega-100-acceptance.json
python scripts/omega_acceptance_gate.py --manifest evidence/omega-100-acceptance.json --enforce
```

The first two commands should succeed on a valid blocked baseline. `--enforce` **must fail** until all 100 independently verified. Logs may disclose sensitive content; only sanitized, explicitly authorized evidence should be copied into a future controlled evidence root.

The status report is a separate control, not an auto-deploy trigger. A complete signed release additionally requires the exact integrated commit, security/owner review, tests on approved platforms, reproducible artifact digest, rollback rehearsal and live deployment receipt. No branch merge, production release, or privilege broadening is authorized by this gate.

## Independent findings addressed (11 Nov 2026)

The inventory job may succeed while 100/100 production acceptance is denied. It is
**not** a deployment check. A separate `workflow_dispatch` job,
`release-admission-deny-only`, runs the CLI with `--enforce` as a hard-failing
command. The job has no secrets, no provider access and no deployment actions;
given the public blocked manifest, its failure is the expected result.
It cannot issue release approval. A trusted, private acceptance runner would
have to supply the exact approved artifact, signed logs, independent auditor
and owner public keys and authenticated test-device receipts before deciding
whether to approve any actual deployment.

The JSON parser now rejects duplicate property names (including nested
objects), NaN and infinity. The evidence receipt rejects unsigned extra fields.
These are control hardening measures, not proof that the system is production-ready.

## Safety correction — requirement proofs are not deployment proofs

The offline gate now reports two deliberately different signals:

- `requirements_verified` is true only if every one of OMEGA-001..100
  contains verifiable signed requirement evidence. Use
  `--enforce-requirements` in an authorized private verification environment
  to enforce this standard alone. It does **not** authorize deployment.
- `production_accepted` remains **false** and `--enforce` denies the release.
  This public repository does not yet implement a trusted independent
  deployment/build/smoke/rollback attestation verifier. Even 100 correctly
  signed test receipts cannot substitute for a deployed, monitored service.

The new positive cryptographic regression deliberately signs all 100
requirement test receipts with **ephemeral test keys** and verifies that
`--enforce-requirements` succeeds while `--enforce` still refuses production.
These are synthetic fixtures, not owner credentials or actual product tests.
The Ed25519 positive unit tests are now required, never skipped for a missing
cryptography package; fail closed if it is unavailable.
