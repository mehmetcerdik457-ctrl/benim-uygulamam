# OMEGA P0 — CI and privacy guard consolidation

This draft does not change the PROJECT OMEGA V2.0 requirements or accept any PR.

- PR #40's grep with matching-line display and ambiguous git-error handling is not acceptable.
- PR #44's admission and workflow-structure diagnosis remain valuable independent tests.
- PR #53's local GitHub Actions job, read-only permissions, quiet scan and fail-closed decision are the chosen base.
- PR #54/#58's binary-aware quiet scan covers Git-tracked binary content as well. It remains heuristic, and is not Gitleaks.
- CI and Privacy Guard now both run local jobs, rather than referencing organization-owned reusable workflows.
- A separate local filename checker reads Git-tracked filenames without printing matches or paths.
- Pinned checkout v4.2.2 and setup-python v5.6.0 action commit references reduce mutable-tag risk. Dependencies and images still need comprehensive lock/digest and vulnerability review.

Acceptance criteria: GitHub Actions jobs on the exact final integration HEAD, real isolated temp-repository tests including match/no-match/error/binary, complete Compose E2E, no secret echo in logs, independent human review and explicit owner approval. Zero-job or action_required never equals a test PASS.

**Not addressed:** historical/commit-history scanning, real secret detection beyond patterns, owner machine connectivity, real IdP, production deployment, paid resources or accounts 476/457. All remain blocked or separate read-only discovery.
