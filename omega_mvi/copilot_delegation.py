"""Fail-closed, no-network Copilot task handoff intent, not an assignment client.

GitHub's agent tasks API public preview supports user-to-server auth but NOT
installation access tokens. This module never touches tokens, task prompt text,
REST calls, issue assignees, or any GitHub write endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from uuid import UUID

REPOSITORY = "mehmetcerdik457-ctrl/benim-uygulamam"
SHA = re.compile(r"[0-9a-f]{40}\Z")


class HandoffDenied(ValueError):
    """Untrusted or incomplete handoff intent."""


@dataclass(frozen=True)
class CopilotHandoffIntent:
    repository: str
    issue_number: int
    trace_id: str
    base_ref: str
    pinned_base_sha: str
    budget_cents: int
    deadline_utc: str
    supported_api: str = "agents/repos/{owner}/{repo}/tasks [public preview]"
    token_boundary: str = "user-to-server only; installation tokens denied"
    status: str = "BLOCKED"
    dry_run: bool = True
    can_dispatch: bool = False
    blockers: tuple[str, ...] = (
        "COPILOT_ENTITLEMENT_UNKNOWN",
        "OWNER_APPROVAL_NOT_VERIFIED",
        "BASE_SHA_NOT_REVALIDATED",
        "NO_APPROVED_USER_TO_SERVER_CREDENTIAL",
        "NO_DISPATCHER_IMPLEMENTED",
    )


def plan_handoff(
    *,
    repository: str,
    issue_number: int,
    trace_id: str,
    base_ref: str,
    pinned_base_sha: str,
    budget_cents: int,
    deadline_utc: str,
) -> CopilotHandoffIntent:
    """Validate a bounded, non-dispatchable intent without recording prompts.

    All fields are metadata only. Do not include task prompt, code, secrets or
    provider credentials. This function NEVER grants or records approval.
    """
    if repository != REPOSITORY:
        raise HandoffDenied("Repository outside allowlist")
    if type(issue_number) is not int or issue_number <= 0:
        raise HandoffDenied("A real positive issue number is required")
    if not isinstance(trace_id, str):
        raise HandoffDenied("Trace ID required")
    try:
        if str(UUID(trace_id)) != trace_id.lower():
            raise ValueError("Noncanonical UUID")
    except ValueError as exc:
        raise HandoffDenied("Valid trace ID required") from exc
    if (not isinstance(base_ref, str) or base_ref != "main"
            and not re.fullmatch(r"omega/[a-z0-9][a-z0-9._/-]{0,100}", base_ref)):
        raise HandoffDenied("Unapproved base branch format")
    if base_ref != "main" and any(segment in ("", ".", "..") for segment in base_ref.split("/")):
        raise HandoffDenied("Traversal or empty branch segment")
    if not isinstance(pinned_base_sha, str) or not SHA.fullmatch(pinned_base_sha):
        raise HandoffDenied("Exact 40-character base SHA required")
    if type(budget_cents) is not int or budget_cents < 0:
        raise HandoffDenied("Non-negative integer cost budget required")
    if not isinstance(deadline_utc, str):
        raise HandoffDenied("Deadline required")
    try:
        parsed = datetime.fromisoformat(deadline_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HandoffDenied("ISO timestamp required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise HandoffDenied("Explicit UTC deadline required")
    return CopilotHandoffIntent(
        repository=repository, issue_number=issue_number,
        trace_id=trace_id, base_ref=base_ref, pinned_base_sha=pinned_base_sha,
        budget_cents=budget_cents, deadline_utc=deadline_utc,
    )
