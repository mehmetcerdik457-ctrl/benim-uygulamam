# Copilot dispatch acceptance gates

This integration is not live until the user-owned credential, eight real open issues, pinned branch SHA and custom agent profiles are independently verified.

- Default: read-only / preview. No automatic task submission.
- Owner approval is required before each dispatch batch.
- Durable SQLite batch claim precedes any remote POST.
- Unknown outcomes remain pending and are never automatically retried.
- No merge, deployment, permission changes, or secrets in prompts.
- Local mock tests are not evidence of live GitHub Copilot execution.

Status: DOCUMENTATION ONLY. No agents have been dispatched by this commit.
