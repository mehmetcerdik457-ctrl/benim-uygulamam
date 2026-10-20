# OMEGA Public Inventory — First real, scoped connector-derived metadata

This dated, public-only snapshot is from an authorized read-only GitHub
repository metadata lookup on 2026-10-20. The connector returned a public
repository and the counts included in `OMEGA_PUBLIC_GITHUB_SNAPSHOT_2026-10-20.json`.
The main SHA was separately read from the branch endpoint. Values may change.

The existing MVI inspector remains a synthetic four-module offline fixture.
The new `omega_bridge.public_inventory` adapter reuses its allowlisted schema
for a **real public repository snapshot**, but performs **no runtime GitHub API
calls**, does not import a token, and grants **no Owner authorization**.

Run offline: `python -m omega_bridge.public_inventory --snapshot docs/evidence/OMEGA_PUBLIC_GITHUB_SNAPSHOT_2026-10-20.json`.
The original PR58 module bytes and 77-byte identity manifest are untouched.

Blocked: Owner-verified provider access, pagination/rate-limit tests, branch/fork
inventory and real private account enumeration remain outside this adapter;
this is **NOT full acceptance of requirement #11**.
