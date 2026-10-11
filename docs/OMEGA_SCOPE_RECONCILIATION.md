# OMEGA scope reconciliation (proposal only)

Date: 2026-10-11. This text does NOT change an effective permission or approve either draft. Source drafts: [PR #19](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/19/files) and [PR #21](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/21/files).

| Control | PR #19 | PR #21 | Conservative proposed rule |
| --- | --- | --- | --- |
| Default policy | read_only, dry_run, deny | same | preserve deny |
| Additional GitHub repos | discover metadata only | denied | deny *agent* additional repo access by default; historical 19-repo owner-authorized connector metadata is not agent authorization |
| Cross-repo approval | cross_repository_write | cross_repository_access | require owner approval for **any** cross-repository access |
| Google Drive | metadata_only | denied | Copilot agent: denied; separately owner-authorized Drive connector work cannot imply Copilot permission |
| Google Cloud | denied until scoped | denied until scoped | denied |
| Local device | denied until scoped | denied; unknown hardware | denied; UNKNOWN |
| Backup upload | owner approval | owner approval | disabled until encryption, integrity, restore verification and approval |
| Secret values | forbidden everywhere | forbidden everywhere | forbidden |

**Important:** This is a *minimum-privilege proposal*. Preserve both original scope.yaml versions in their respective draft branches. Do not overwrite either branch, merge, add an organization-wide reader, remove workflow approval, or infer user approval from repository ownership. A future approved policy change requires issue, diff, exact resource/permission/purpose, owner decision, independent review, tests, and rollback.

Bounded inventory already performed by a connected owner account is not the same as giving Copilot access to 19 repositories. This PUBLIC repository stores no private inventory.

Approval gates: owner selects an exact repository and permitted read operations; reviewers verify that code enforces deny; test forbidden cross-repo access; only then consider a non-draft merge.
