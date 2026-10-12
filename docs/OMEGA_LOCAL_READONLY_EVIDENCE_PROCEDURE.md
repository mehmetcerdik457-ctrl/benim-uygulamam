# OMEGA-014/019/020 — Read-only local evidence & provenance procedure

**State: DESIGN + SYNTHETIC CONTRACT ONLY. Live owner-device scanning BLOCKED.**

Source of authority: PROJECT OMEGA V2.0 requirements #14, #19 and #20. GitHub scope.yaml at PR #58 head `044c558b2b28e05929a9acd79a639a32092ab187` explicitly says `local_device.access: denied`. Private `0.1.4-dev` commit `053e75d5591c836714d27d2d8b9b3f74c4464b9f` is a different and **uninspected** codebase. Do not treat CI, a hosted runner, or the public tree as that codebase.

## Authorization gate (must precede a real scan)

1. Obtain an authenticated owner approval bound to actor, exact canonical **root path or mount ID**, device identity, purpose, data classes, permitted descendants, time window, maximum bytes/files, output location, retention deadline and revocation ID. Approval must be verified *outside the model* by a trusted policy service; a request text, path string, self-declared `approved=true`, or tool availability is not authority.
2. Require a dedicated read-only mount/snapshot, or an approved forensic write blocker where evidence preservation matters. A userspace `open(..., O_RDONLY)` **does not guarantee no writes to source media**: atime, journaling and filesystem services may update metadata. If read-only mount cannot be attested, stop.
3. Block physical/raw devices, other partitions, network shares, cloud sync folders, keys, secrets, credentials, private snapshots, and owner disks unless each is explicitly covered. Physical disk imaging is **a separate forensic acquisition task** with its own written scope, expert procedure and approval. Never improvise it as folder traversal.
4. Use fd-relative traversal with `O_NOFOLLOW` / no-follow equivalents, verify device + inode and path containment on every entry, reject symlinks, junctions, reparse points, hardlink anomalies requiring review, special devices, sockets, FIFOs, mount boundary crossings and race/inode changes. Deny on errors, unsupported filesystem properties and unverified ACL/XAttr capture.
5. Acquire the smallest necessary set of metadata without collecting unrelated private content. No raw bytes, real paths, PII, tokens or unredacted filenames may enter a public issue, Git history, model prompt, RAG index or logs.

**Current code intentionally has no local traversal API.** `omega_mvi/inspection/provenance/` only hashes caller-supplied `synthetic://` fixture bytes; any `file://` or private GitHub source is denied. This protects the existing modules from an unauthorized scan path.

## Evidence chain & reproducible procedure (future owner-approved implementation)

For each source, record a **separately protected** evidence envelope with `case_id` (opaque), `source_ref` (owner-private alias), `relative_path` (owner-private), `source_version`, `source_device_id`, `owner_ref`, verified ACL/access class, classification, retention policy, verification instant (UTC), acquisition/tool version, scope approval reference, acquisition outcome and failure reason. Tie the envelope to an indexed artifact using content SHA-256 **and** a canonical metadata SHA-256. Do not put raw restricted values in the index. Explicit unknown metadata must be marked unverified rather than substituted with zeros.

Snapshot fields for regular files: size, file type, mtime_ns, POSIX mode, uid, gid, and separately digested **authorized** ACL/xattr metadata. Windows/other filesystems need an equivalent schema before activation. Also preserve path-identity, authorized ownership/access level, last verification and retention deadline. Content digest and metadata digest change independently; versioned index snapshots link using `previous_index_sha256`.

At every custody transfer record actor identity, device, timestamp, purpose, prior/new custodian, evidence manifest digest, signature verification, scope and retention status, and outcome in an append-only controlled audit log. SHA-256 is *not* a signature; require independent signing/key management and trusted timestamps to attribute custody. Store sensitive source paths/hash manifests in owner-private encrypted evidence storage with access/audit, not in public Issue #25.

Run `compare_indices(old, new)` for added, removed, content-only drift, metadata-only drift and provenance drift. Any mismatch, missing link, ACL read error, inode race, unknown owner, or authorization expiry must be surfaced as FAIL/BLOCKED—not silently accepted. A contents-only index is inadequate.

## Synthetic contract

`omega_mvi/inspection/provenance/__init__.py` exposes `make_fixture_record`, `build_index`, `compare_indices`. The code makes **no filesystem, GitHub, cloud or network call**; stores hashes and fields, not supplied data bytes, and refuses `restricted` or live source references. Test: `PYTHONPATH=. python -m pytest -q omega_mvi/inspection/provenance/test_index.py`; run against exact PR SHA and retain the runner URL before promoting any test status.

## Integrator requests — do not silently edit common files

- Keep `scope.yaml` local-device permission at **denied** until the owner and security reviewer approve a cryptographically verified scope service. After approval, integrator owns changes to common policy and route wiring.
- PostgreSQL schema migration to a constrained `omega_provenance` table, least-privilege role/RLS, FK to scoped source, immutable custody event ledger, retention/deletion policies and auditable backups belongs to the **database/integration** owner. No migration or credential grant is included here.
- Do not connect to RAG, UI, agent executors or task coordinator until ACL enforcement, redaction, independent authorization and migration/rollback tests pass.
- Priorities: #14 and #19 are post-MVI in the current matrix; #20 is P1 MVI but still depends on #17. No DONE or production claim.

## Acceptance gates

- OMEGA-014: owner-approved exact roots, RO mount evidence, no traversal escape, symlink/race/atime handling, bounded negative tests on a consenting owner-controlled test device; live device **NOT_TESTED**.
- OMEGA-019: fixture metadata & content SHA drift, version chain, explicit unknown fields and tamper detection; synthetic tests can PASS, full filesystem validation **NOT_TESTED**.
- OMEGA-020: source, opaque ownership, ACL/access, UTC verification and retention linked to immutable signed provenance records and least-privilege storage; synthetic schema can PASS, persistent DB and signed custody **NOT_IMPLEMENTED**.


## Incremental synthetic review contract (2026-10-12)

`verify_index_chain(snapshots, expected_genesis_sha256, expected_tip_sha256)`
now checks every snapshot version, index digest and prior-link digest against
independently supplied initial/final SHA-256 checkpoints. It rejects missing
middle entries, replay, order changes, truncated tips and recomputed but
unanchored alternate histories. The expected checkpoints must come from a
**separate trusted, preferably signed and immutable record**; copying hashes
from the same untrusted snapshots does not authenticate the chain.

`review_provenance_changes(old, new)` produces an **advisory** report:
source addition, removal, source-version, opaque owner, access class,
retention policy, POSIX mode, UID, GID, ACL digest or xattr digest changes
require external human review. Mtime-only changes remain integrity evidence,
not a grant of authority. The report always returns
`approval_granted=false`, `deletion_authorized=false`,
`identity_verified=false`, and `storage_retention_enforced=false`.
It contains only synthetic fixture aliases; it reads no disk and does not
touch a database. A report flag is never an authenticated human approval.

**Retention gap:** the fixture's `verified_at` is a verification instant,
**not** a trusted original acquisition date. The presence of
`retention_days` does not prove a lawful expiry clock, legal hold, erasure,
or backup copy deletion. The eventual owner-approved persistence schema
must anchor collection/acquisition time separately, retain immutable
retention-policy decisions and prove authorized expiry actions. Do not
recalculate retention from every subsequent verification timestamp.

**Remaining independent controls:** authenticated/signed custody events,
private anchor storage, real ACL enumeration, inode/race/atime controls,
external source allowlist, legal hold, database tenant isolation and
restore/migration/retention tests. None are implied by this fixture-only code.
