"""Pure synthetic branch protection contract tests: no writes."""
import copy
import unittest
from omega_mvi.pr_security.protection import (
    SECURITY_CHECK, inspect_main_protection
)

SEC_ID = 101
CI_ID = 15368


def policy():
    return {
        "enforce_admins": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
        "required_conversation_resolution": {"enabled": True},
        "required_status_checks": {
            "strict": True,
            "checks": [
                {"context": SECURITY_CHECK, "app_id": SEC_ID},
                {"context": "baseline", "app_id": CI_ID},
            ],
        },
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": True,
            "require_last_push_approval": True,
            "bypass_pull_request_allowances": {"users": [], "teams": [], "apps": []},
        },
    }


def judge(p=None, *, branch=None, sec=SEC_ID, ci=CI_ID):
    return inspect_main_protection(
        {"name": "main", "protected": True} if branch is None else branch,
        policy() if p is None else p,
        trusted_security_app_id=sec,
        trusted_ci_app_id=ci,
        ci_check_name="baseline",
    )


class ProtectionContractTests(unittest.TestCase):
    def test_full_policy_is_purely_advisory(self):
        result = judge()
        self.assertTrue(result.complete)
        self.assertFalse(result.authoritative)

    def test_unprotected_main_denied(self):
        self.assertIn("MAIN_NOT_PROTECTED", judge(branch={"name": "main", "protected": False}).blockers)

    def test_403_or_missing_protection_denied(self):
        r = judge(p={})
        self.assertFalse(r.complete)
        self.assertIn("STRICT_STATUS_CHECKS_NOT_ENFORCED", r.blockers)

    def test_missing_app_config_denied(self):
        self.assertFalse(judge(sec=0).complete)

    def test_same_ci_and_security_app_denied(self):
        self.assertFalse(judge(sec=CI_ID).complete)

    def test_admin_bypass_denied(self):
        p = policy(); p["enforce_admins"]["enabled"] = False
        self.assertFalse(judge(p).complete)

    def test_force_push_denied(self):
        p = policy(); p["allow_force_pushes"]["enabled"] = True
        self.assertFalse(judge(p).complete)

    def test_branch_delete_denied(self):
        p = policy(); p["allow_deletions"]["enabled"] = True
        self.assertFalse(judge(p).complete)

    def test_missing_security_check_denied(self):
        p = policy(); p["required_status_checks"]["checks"].pop(0)
        self.assertFalse(judge(p).complete)

    def test_security_check_any_app_denied(self):
        p = policy(); p["required_status_checks"]["checks"][0]["app_id"] = -1
        self.assertFalse(judge(p).complete)

    def test_wrong_ci_source_denied(self):
        p = policy(); p["required_status_checks"]["checks"][1]["app_id"] = -1
        self.assertFalse(judge(p).complete)

    def test_duplicate_check_name_denied(self):
        p = policy()
        p["required_status_checks"]["checks"].append({"context": SECURITY_CHECK, "app_id": SEC_ID})
        self.assertFalse(judge(p).complete)

    def test_strict_false_denied(self):
        p = policy(); p["required_status_checks"]["strict"] = False
        self.assertFalse(judge(p).complete)

    def test_missing_review_required_denied(self):
        p = policy(); del p["required_pull_request_reviews"]
        self.assertFalse(judge(p).complete)

    def test_zero_approvals_denied(self):
        p = policy(); p["required_pull_request_reviews"]["required_approving_review_count"] = 0
        self.assertFalse(judge(p).complete)

    def test_stale_reviews_not_dismissed_denied(self):
        p = policy(); p["required_pull_request_reviews"]["dismiss_stale_reviews"] = False
        self.assertFalse(judge(p).complete)

    def test_codeowner_review_missing_denied(self):
        p = policy(); p["required_pull_request_reviews"]["require_code_owner_reviews"] = False
        self.assertFalse(judge(p).complete)

    def test_last_push_review_missing_denied(self):
        p = policy(); p["required_pull_request_reviews"]["require_last_push_approval"] = False
        self.assertFalse(judge(p).complete)

    def test_bypass_allowance_denied(self):
        p = policy()
        p["required_pull_request_reviews"]["bypass_pull_request_allowances"]["users"] = [{"login": "admin"}]
        self.assertFalse(judge(p).complete)

    def test_missing_conversation_resolution_denied(self):
        p = policy(); p["required_conversation_resolution"]["enabled"] = False
        self.assertFalse(judge(p).complete)

    def test_ruleset_alone_not_claimed_as_enforced(self):
        self.assertFalse(judge(p={}).complete)


if __name__ == "__main__":
    unittest.main()
