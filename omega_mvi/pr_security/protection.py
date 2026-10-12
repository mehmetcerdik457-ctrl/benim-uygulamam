"""Non-authoritative premerge protection evidence audit.

Requires REAL GET /branches/main/protection evidence in production. Synthetic
data only demonstrates contract behavior; this code never changes rulesets.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

REPOSITORY = "mehmetcerdik457-ctrl/benim-uygulamam"
SECURITY_CHECK = "omega/security-review"


@dataclass(frozen=True)
class ProtectionFinding:
    complete: bool
    blockers: tuple[str, ...]
    authoritative: bool = False


def inspect_main_protection(
    branch: Mapping[str, Any],
    protection: Mapping[str, Any] | None,
    *,
    trusted_security_app_id: int,
    trusted_ci_app_id: int,
    ci_check_name: str,
) -> ProtectionFinding:
    """Require explicit provider-enforced review and app-locked Checks."""
    blockers: list[str] = []
    if (not isinstance(branch, Mapping) or branch.get("name") != "main"
            or branch.get("protected") is not True):
        blockers.append("MAIN_NOT_PROTECTED")
    if (not isinstance(protection, Mapping) or
            type(trusted_security_app_id) is not int or trusted_security_app_id <= 0 or
            type(trusted_ci_app_id) is not int or trusted_ci_app_id <= 0 or
            trusted_security_app_id == trusted_ci_app_id or
            not isinstance(ci_check_name, str) or not ci_check_name
            or ci_check_name == SECURITY_CHECK):
        blockers.append("PROTECTION_OR_TRUSTED_APP_CONFIG_MISSING")
        return ProtectionFinding(False, tuple(blockers))

    def enabled(name: str) -> bool:
        obj = protection.get(name)
        return isinstance(obj, Mapping) and obj.get("enabled") is True

    def disabled(name: str) -> bool:
        obj = protection.get(name)
        return isinstance(obj, Mapping) and obj.get("enabled") is False

    if not enabled("enforce_admins"):
        blockers.append("ADMIN_BYPASS_NOT_CLOSED")
    if not disabled("allow_force_pushes"):
        blockers.append("FORCE_PUSH_POLICY_UNKNOWN_OR_ENABLED")
    if not disabled("allow_deletions"):
        blockers.append("BRANCH_DELETE_POLICY_UNKNOWN_OR_ENABLED")
    if not enabled("required_conversation_resolution"):
        blockers.append("UNRESOLVED_CONVERSATIONS_NOT_ENFORCED")
    required = protection.get("required_status_checks")
    if not isinstance(required, Mapping) or required.get("strict") is not True:
        blockers.append("STRICT_STATUS_CHECKS_NOT_ENFORCED")
    else:
        checks = required.get("checks")
        if not isinstance(checks, list):
            blockers.append("APP_LOCKED_CHECKS_NOT_AVAILABLE")
        else:
            for name, app_id in ((SECURITY_CHECK, trusted_security_app_id),
                                 (ci_check_name, trusted_ci_app_id)):
                matches = [x for x in checks
                           if isinstance(x, Mapping) and x.get("context") == name]
                if len(matches) != 1 or matches[0].get("app_id") != app_id:
                    blockers.append("MISSING_OR_UNTRUSTED_REQUIRED_CHECK:" + name)

    reviews = protection.get("required_pull_request_reviews")
    if not isinstance(reviews, Mapping):
        blockers.append("REVIEW_PROTECTION_MISSING")
    else:
        count = reviews.get("required_approving_review_count")
        if type(count) is not int or count < 1:
            blockers.append("HUMAN_REVIEW_COUNT_NOT_ENFORCED")
        if reviews.get("dismiss_stale_reviews") is not True:
            blockers.append("STALE_APPROVAL_DISMISSAL_DISABLED")
        if reviews.get("require_code_owner_reviews") is not True:
            blockers.append("CODEOWNERS_REVIEW_NOT_REQUIRED")
        if reviews.get("require_last_push_approval") is not True:
            blockers.append("LAST_PUSH_REVIEW_NOT_REQUIRED")
        allowances = reviews.get("bypass_pull_request_allowances")
        if allowances is not None and (
            not isinstance(allowances, Mapping) or
            any(allowances.get(kind) for kind in ("users", "teams", "apps"))
        ):
            blockers.append("REVIEW_BYPASS_ALLOWANCES_PRESENT")
    return ProtectionFinding(not blockers, tuple(dict.fromkeys(blockers)))
