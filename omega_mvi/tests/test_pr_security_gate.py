"""Offline, no-token P0 contract tests for the read-only PR gate."""
import copy
import unittest
from omega_mvi.pr_security.gate import (
    EvidenceError, GitHubReadOnlyClient, evaluate, REPOSITORY,
)

SHA = "a" * 40
OTHER = "b" * 40
APP = 132
CHECK = "security-ci"
OWNER = "approved-human"


def sample(path="README.md"):
    return {
        "pr": {
            "number": 100, "state": "open", "draft": False,
            "head": {"sha": SHA, "repo": {"full_name": REPOSITORY}},
            "base": {"ref": "main"}, "user": {"login": "pull-author"},
        },
        "rechecked_sha": SHA,
        "main": {"name": "main", "protected": True},
        "files": [{"filename": path, "patch": "@@ -1 +1 @@\n-old\n+new"}],
        "checks": [{"name": CHECK, "head_sha": SHA, "app": {"id": APP},
                    "status": "completed", "conclusion": "success"}],
        "runs": [{"name": "CI", "head_sha": SHA, "event": "pull_request",
                  "status": "completed", "conclusion": "success"}],
        "reviews": [],
    }


def judge(v, **config):
    return evaluate(
        v, expected_sha=config.get("expected_sha", SHA),
        trusted_check_app_id=config.get("app_id", APP),
        required_checks=config.get("required_checks", (CHECK,)),
        authorized_human_reviewers=config.get("reviewers", frozenset({OWNER})),
    )


class ReviewGateTests(unittest.TestCase):
    def test_safe_case_is_advisory_not_check_publish(self):
        result = judge(sample())
        self.assertTrue(result.accepted)
        self.assertFalse(result.authoritative)
        self.assertEqual(result.risk, "NORMAL")

    def test_sha_changed_during_read_is_denied(self):
        e = sample(); e["rechecked_sha"] = OTHER
        with self.assertRaises(EvidenceError): judge(e)

    def test_expected_sha_mismatch_is_denied(self):
        with self.assertRaises(EvidenceError): judge(sample(), expected_sha=OTHER)

    def test_draft_is_denied(self):
        e = sample(); e["pr"]["draft"] = True
        with self.assertRaises(EvidenceError): judge(e)

    def test_fork_head_denied(self):
        e = sample(); e["pr"]["head"]["repo"]["full_name"] = "evil/repo"
        with self.assertRaises(EvidenceError): judge(e)

    def test_patch_missing_denied(self):
        e = sample(); e["files"][0]["patch"] = None
        with self.assertRaises(EvidenceError): judge(e)

    def test_unprotected_main_blocks(self):
        e = sample(); e["main"]["protected"] = False
        self.assertIn("MAIN_NOT_PROTECTED_OR_UNKNOWN", judge(e).blockers)

    def test_action_required_blocks(self):
        e = sample(); e["runs"][0]["conclusion"] = "action_required"
        self.assertIn("FAILED_BLOCKED_OR_STALE_WORKFLOW_RUN", judge(e).blockers)

    def test_failed_pr_run_blocks(self):
        e = sample(); e["runs"][0]["conclusion"] = "failure"
        self.assertFalse(judge(e).accepted)

    def test_failed_check_blocks(self):
        e = sample(); e["checks"][0]["conclusion"] = "failure"
        self.assertFalse(judge(e).accepted)

    def test_check_must_be_exact_sha_and_app(self):
        e = sample(); e["checks"][0]["app"]["id"] = 0
        self.assertIn("REQUIRED_CHECK_UNTRUSTED:" + CHECK, judge(e).blockers)

    def test_missing_required_check_blocks(self):
        e = sample(); e["checks"] = []
        self.assertIn("REQUIRED_CHECK_MISSING:" + CHECK, judge(e).blockers)

    def test_duplicate_required_check_blocks(self):
        e = sample(); e["checks"].append(copy.deepcopy(e["checks"][0]))
        self.assertIn("REQUIRED_CHECK_AMBIGUOUS:" + CHECK, judge(e).blockers)

    def test_high_risk_requires_human(self):
        e = sample(".github/workflows/deploy.yml")
        verdict = judge(e)
        self.assertEqual(verdict.risk, "HIGH")
        self.assertIn("AUTHORIZED_SHA_BOUND_HUMAN_REVIEW_MISSING", verdict.blockers)

    def test_agent_approval_not_accepted_as_human(self):
        e = sample("omega_mvi/security/auth.py")
        e["reviews"] = [{"state": "APPROVED", "commit_id": SHA,
                         "user": {"login": OWNER, "type": "Bot"}}]
        self.assertFalse(judge(e).accepted)

    def test_owner_authorized_current_sha_approval_required(self):
        e = sample("omega_mvi/security/auth.py")
        e["reviews"] = [{"state": "APPROVED", "commit_id": OTHER,
                         "user": {"login": OWNER, "type": "User"}}]
        self.assertFalse(judge(e).accepted)
        e["reviews"][0]["commit_id"] = SHA
        self.assertTrue(judge(e).accepted)

    def test_pr_author_self_approval_denied(self):
        e = sample(".github/workflows/deploy.yml")
        e["reviews"] = [{"state": "APPROVED", "commit_id": SHA,
                         "user": {"login": "pull-author", "type": "User"}}]
        self.assertFalse(judge(e, reviewers=frozenset({"pull-author"})).accepted)

    def test_superseded_approval_no_longer_counts(self):
        e = sample(".github/workflows/deploy.yml")
        person = {"login": OWNER, "type": "User"}
        e["reviews"] = [
            {"state": "APPROVED", "commit_id": SHA, "user": person},
            {"state": "CHANGES_REQUESTED", "commit_id": SHA, "user": person},
        ]
        result = judge(e)
        self.assertFalse(result.accepted)
        self.assertIn("OUTSTANDING_CHANGES_REQUESTED", result.blockers)

    def test_missing_policy_configuration_denied(self):
        with self.assertRaises(EvidenceError): judge(sample(), reviewers=frozenset())

    def test_truncated_checks_denied(self):
        e = sample(); e["checks"] = [e["checks"][0]] * 101
        with self.assertRaises(EvidenceError): judge(e)

    def test_cross_repo_client_denied(self):
        with self.assertRaises(EvidenceError): GitHubReadOnlyClient(repository="attacker/repo")

    def test_read_only_transport_never_uses_write_methods(self):
        client = GitHubReadOnlyClient()
        self.assertFalse(hasattr(client, "post"))
        self.assertFalse(hasattr(client, "publish_check"))


if __name__ == "__main__":
    unittest.main()
