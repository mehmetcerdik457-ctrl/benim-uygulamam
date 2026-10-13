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
            "head": {"sha": SHA, "ref": "pr-security", "repo": {"full_name": REPOSITORY}},
            "base": {"ref": "main", "sha": OTHER, "repo": {"full_name": REPOSITORY}}, "user": {"login": "pull-author"},
        },
        "rechecked_sha": SHA,
        "main": {"name": "main", "protected": True, "commit": {"sha": OTHER}},
        "files": [{"filename": path, "patch": "@@ -1 +1 @@\n-old\n+new"}],
        "checks": [{"name": CHECK, "head_sha": SHA, "app": {"id": APP},
                    "status": "completed", "conclusion": "success"}],
        "runs": [{"name": "CI", "head_sha": SHA, "event": "pull_request",
                  "head_repository": {"full_name": REPOSITORY},
                  "pull_requests": [{"number": 100, "head": {"sha": SHA}, "base": {"sha": OTHER}}],
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
        e["reviews"] = [{"state": "APPROVED", "commit_id": SHA, "submitted_at": "2026-10-11T10:00:00Z",
                         "user": {"login": OWNER, "type": "Bot"}}]
        self.assertFalse(judge(e).accepted)

    def test_owner_authorized_current_sha_approval_required(self):
        e = sample("omega_mvi/security/auth.py")
        e["reviews"] = [{"state": "APPROVED", "commit_id": OTHER, "submitted_at": "2026-10-11T10:00:00Z",
                         "user": {"login": OWNER, "type": "User"}}]
        self.assertFalse(judge(e).accepted)
        e["reviews"][0]["commit_id"] = SHA
        self.assertTrue(judge(e).accepted)

    def test_pr_author_self_approval_denied(self):
        e = sample(".github/workflows/deploy.yml")
        e["reviews"] = [{"state": "APPROVED", "commit_id": SHA, "submitted_at": "2026-10-11T10:00:00Z",
                         "user": {"login": "pull-author", "type": "User"}}]
        self.assertFalse(judge(e, reviewers=frozenset({"pull-author"})).accepted)

    def test_superseded_approval_no_longer_counts(self):
        e = sample(".github/workflows/deploy.yml")
        person = {"login": OWNER, "type": "User"}
        e["reviews"] = [
            {"state": "APPROVED", "commit_id": SHA, "submitted_at": "2026-10-11T10:00:00Z", "user": person},
            {"state": "CHANGES_REQUESTED", "commit_id": SHA, "submitted_at": "2026-10-11T11:00:00Z", "user": person},
        ]
        result = judge(e)
        self.assertFalse(result.accepted)
        self.assertIn("OUTSTANDING_CHANGES_REQUESTED", result.blockers)

    def test_missing_policy_configuration_denied(self):
        with self.assertRaises(EvidenceError): judge(sample(), reviewers=frozenset())

    def test_truncated_checks_denied(self):
        e = sample(); e["checks"] = [e["checks"][0]] * 101
        with self.assertRaises(EvidenceError): judge(e)

    def test_same_sha_but_wrong_pr_number_blocks(self):
        e = sample(); e["runs"][0]["pull_requests"][0]["number"] = 999
        self.assertIn("WORKFLOW_NOT_LINKED_TO_EXACT_PR_AND_BASE", judge(e).blockers)

    def test_same_sha_but_wrong_base_sha_blocks(self):
        e = sample(); e["runs"][0]["pull_requests"][0]["base"]["sha"] = SHA
        self.assertFalse(judge(e).accepted)

    def test_same_sha_but_wrong_repository_blocks(self):
        e = sample(); e["runs"][0]["head_repository"]["full_name"] = "other/repo"
        self.assertFalse(judge(e).accepted)

    def test_unlinked_pr_run_blocks(self):
        e = sample(); e["runs"][0]["pull_requests"] = []
        self.assertFalse(judge(e).accepted)

    def test_missing_run_provenance_blocks(self):
        e = sample(); e["runs"][0].pop("head_repository")
        self.assertIn("WORKFLOW_PR_IDENTITY_MISSING", judge(e).blockers)

    def test_stacked_pr_cannot_claim_main_acceptance(self):
        e = sample()
        e["pr"]["base"]["ref"] = "omega/some-branch"
        self.assertIn("STACKED_PR_NOT_MAIN_ACCEPTANCE", judge(e).blockers)

    def test_changed_base_tip_blocks(self):
        e = sample(); e["pr"]["base"]["sha"] = SHA
        self.assertIn("BASE_SHA_NOT_CURRENT_MAIN", judge(e).blockers)

    def test_arbitrary_python_is_high_risk(self):
        e = sample("src/main.py")
        self.assertEqual("HIGH", judge(e).risk)
        self.assertFalse(judge(e).accepted)

    def test_terraform_changes_are_high_risk(self):
        e = sample("infra/main.tf")
        self.assertEqual("HIGH", judge(e).risk)
        self.assertFalse(judge(e).accepted)

    def test_docs_only_path_is_normal_risk(self):
        e = sample("docs/GUIDE.md")
        self.assertEqual("NORMAL", judge(e).risk)
        self.assertTrue(judge(e).accepted)

    def test_blank_patch_denied(self):
        e = sample(); e["files"][0]["patch"] = ""
        with self.assertRaises(EvidenceError): judge(e)

    def test_missing_review_timestamp_denied(self):
        e = sample("src/main.py")
        e["reviews"] = [{"state": "APPROVED", "commit_id": SHA,
                         "user": {"login": OWNER, "type": "User"}}]
        self.assertIn("REVIEW_TIMESTAMP_MISSING", judge(e).blockers)

    def test_reviews_sort_by_submission_time(self):
        e = sample("src/main.py")
        person = {"login": OWNER, "type": "User"}
        e["reviews"] = [
            {"state": "CHANGES_REQUESTED", "commit_id": SHA,
             "submitted_at": "2026-10-11T12:00:00Z", "user": person},
            {"state": "APPROVED", "commit_id": SHA,
             "submitted_at": "2026-10-11T11:00:00Z", "user": person},
        ]
        self.assertFalse(judge(e).accepted)

    def test_pr_base_repo_mismatch_denied(self):
        e = sample(); e["pr"]["base"]["repo"]["full_name"] = "evil/repo"
        with self.assertRaises(EvidenceError): judge(e)

    def test_collector_rechecks_base_sha(self):
        client = GitHubReadOnlyClient()
        fresh = sample()
        original = copy.deepcopy(fresh["pr"])
        changed = copy.deepcopy(original)
        changed["base"]["sha"] = SHA
        calls = [original, fresh["files"], {"total_count": 1, "check_runs": fresh["checks"]},
                 {"total_count": 1, "workflow_runs": fresh["runs"]},
                 fresh["reviews"], fresh["main"], changed]
        client._get = lambda path: calls.pop(0)
        with self.assertRaises(EvidenceError): client.snapshot(100)

    def test_collector_rechecks_draft_state(self):
        client = GitHubReadOnlyClient()
        fresh = sample()
        original = copy.deepcopy(fresh["pr"])
        changed = copy.deepcopy(original)
        changed["draft"] = True
        calls = [original, fresh["files"], {"total_count": 1, "check_runs": fresh["checks"]},
                 {"total_count": 1, "workflow_runs": fresh["runs"]},
                 fresh["reviews"], fresh["main"], changed]
        client._get = lambda path: calls.pop(0)
        with self.assertRaises(EvidenceError): client.snapshot(100)

    def test_collector_rejects_wrong_pr_number(self):
        client = GitHubReadOnlyClient()
        wrong = sample()["pr"]
        client._get = lambda path: wrong
        with self.assertRaises(EvidenceError): client.snapshot(123)

    def test_cross_repo_client_denied(self):
        with self.assertRaises(EvidenceError): GitHubReadOnlyClient(repository="attacker/repo")

    def test_read_only_transport_never_uses_write_methods(self):
        client = GitHubReadOnlyClient()
        self.assertFalse(hasattr(client, "post"))
        self.assertFalse(hasattr(client, "publish_check"))


if __name__ == "__main__":
    unittest.main()
