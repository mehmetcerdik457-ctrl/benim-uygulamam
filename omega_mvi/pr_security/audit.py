"""Two-layer, GET-only premerge audit: PR evidence and enforced protection.

No merge, Checks publisher or actual GitHub branch protection mutation.
This is advisory even when both independent evidence layers are satisfied.
"""
from __future__ import annotations
from dataclasses import dataclass

from omega_mvi.pr_security.gate import (
    EvidenceError, GitHubReadOnlyClient, _pr_identity, evaluate,
)
from omega_mvi.pr_security.protection import inspect_main_protection


@dataclass(frozen=True)
class PremergeAssessment:
    head_sha: str
    blockers: tuple[str, ...]
    advisory_clear: bool
    authoritative: bool = False
    may_merge: bool = False


def inspect_live_premerge(
    client: GitHubReadOnlyClient,
    *,
    pr_number: int,
    expected_head_sha: str,
    trusted_security_app_id: int,
    trusted_ci_app_id: int,
    required_checks: tuple[str, ...],
    ci_check_name: str,
    authorized_human_reviewers: frozenset[str],
) -> PremergeAssessment:
    """Treat any GitHub API outage, 403, missing review or stale HEAD as DENY.

    Exact GitHub branch-protection state may be 403 to a restricted App.
    A 403 MUST remain a failure, not a reason to bypass this check.
    """
    try:
        snapshot = client.snapshot(pr_number)
        verdict = evaluate(
            snapshot,
            expected_sha=expected_head_sha,
            trusted_check_app_id=trusted_security_app_id,
            required_checks=required_checks,
            authorized_human_reviewers=authorized_human_reviewers,
        )
        # This is a separate admin-sensitive GET and cannot be inferred from
        # /branches/main protected=True alone. Permission failure denies.
        protection = client._get("/branches/main/protection")
        policy = inspect_main_protection(
            snapshot["main"], protection,
            trusted_security_app_id=trusted_security_app_id,
            trusted_ci_app_id=trusted_ci_app_id,
            ci_check_name=ci_check_name,
        )
        # Revalidate mutable PR and main ref AFTER policy collection.
        last_pr = client._get(f"/pulls/{pr_number}")
        if _pr_identity(last_pr) != _pr_identity(snapshot["pr"]):
            raise EvidenceError("PR identity changed after policy collection")
        last_main = client._get("/branches/main")
        before = snapshot["main"]
        if (not isinstance(last_main, dict) or not isinstance(before, dict)
                or not isinstance(last_main.get("commit"), dict)
                or not isinstance(before.get("commit"), dict)
                or last_main["commit"].get("sha") != before["commit"].get("sha")
                or last_main.get("protected") != before.get("protected")):
            raise EvidenceError("Main HEAD or protection changed during audit")
        blockers = tuple(dict.fromkeys((*verdict.blockers, *policy.blockers)))
        return PremergeAssessment(
            head_sha=expected_head_sha,
            blockers=blockers,
            advisory_clear=bool(verdict.accepted and policy.complete),
        )
    except Exception:
        # Error types/messages may include credentials/URLs in other clients:
        # never publish the exception text to a verdict.
        return PremergeAssessment(
            head_sha=expected_head_sha,
            blockers=("AUDITOR_UNAVAILABLE_STALE_OR_FORBIDDEN",),
            advisory_clear=False,
        )
