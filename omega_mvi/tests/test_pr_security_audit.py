"""Offline end-to-end premerge verdict tests: no live GitHub access."""
import copy
import unittest
from omega_mvi.pr_security.audit import inspect_live_premerge
from omega_mvi.pr_security.gate import EvidenceError, REPOSITORY

SHA = "a" * 40
BASE = "b" * 40
CI_APP = 15368
SEC_APP = 112
REVIEWER = "approved-human"


def sample():
    pr = {
        "number": 65, "draft": False, "state": "open",
        "head": {"sha": SHA, "ref": "ready",
                 "repo": {"full_name": REPOSITORY}},
        "base": {"sha": BASE, "ref": "main",
                 "repo": {"full_name": REPOSITORY}},
        "user": {"login": "author"},
    }
    main = {"name": "main", "protected": True, "commit": {"sha": BASE}}
    return {
        "pr": pr, "main": main, "rechecked_sha": SHA,
        "files": [{"filename": "docs/readme.md", "patch": "@@ -1 +1 @@\n-old\n+new"}],
        "checks": [{"name": "omega/security-review", "head_sha": SHA,
                    "app": {"id": SEC_APP}, "status": "completed",
                    "conclusion": "success"}],
        "runs": [{"name": "CI", "head_sha": SHA, "event": "pull_request",
                  "head_repository": {"full_name": REPOSITORY},
                  "pull_requests": [{"number": 65, "head": {"sha": SHA},
                                     "base": {"sha": BASE}}],
                  "status": "completed", "conclusion": "success"}],
        "reviews": [],
    }


def protection():
    return {
        "enforce_admins": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
        "required_conversation_resolution": {"enabled": True},
        "required_status_checks": {
            "strict": True,
            "checks": [
                {"context": "omega/security-review", "app_id": SEC_APP},
                {"context": "baseline", "app_id": CI_APP},
            ],
        },
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": True,
            "require_last_push_approval": True,
        },
    }


class FakeClient:
    def __init__(self, *, evidence=None, policy=None, outage=False):
        self.s = sample() if evidence is None else evidence
        self.p = protection() if policy is None else policy
        self.outage = outage

    def snapshot(self, number):
        if self.outage:
            raise EvidenceError("Synthetic provider outage")
        return copy.deepcopy(self.s)

    def _get(self, endpoint):
        if self.outage:
            raise EvidenceError("Synthetic provider outage")
        if endpoint == "/branches/main/protection":
            if self.p == 403:
                raise EvidenceError("403 permission denied")
            return copy.deepcopy(self.p)
        if endpoint == "/branches/main":
            return copy.deepcopy(self.s["main"])
        if endpoint == "/pulls/65":
            return copy.deepcopy(self.s["pr"])
        raise EvidenceError("Unexpected read")


def judge(client=None, **kwargs):
    return inspect_live_premerge(
        FakeClient() if client is None else client,
        pr_number=65, expected_head_sha=kwargs.get("sha", SHA),
        trusted_security_app_id=SEC_APP, trusted_ci_app_id=CI_APP,
        required_checks=("omega/security-review",),
        ci_check_name="baseline",
        authorized_human_reviewers=frozenset({REVIEWER}),
    )


class LivePremergeAuditTests(unittest.TestCase):
    def test_all_synthetic_evidence_is_still_advisory(self):
        r = judge()
        self.assertTrue(r.advisory_clear)
        self.assertFalse(r.authoritative)
        self.assertFalse(r.may_merge)

    def test_protection_403_is_blocked(self):
        r = judge(FakeClient(policy=403))
        self.assertFalse(r.advisory_clear)
        self.assertEqual(r.blockers, ("AUDITOR_UNAVAILABLE_STALE_OR_FORBIDDEN",))

    def test_provider_offline_is_blocked(self):
        self.assertFalse(judge(FakeClient(outage=True)).advisory_clear)

    def test_missing_required_security_check_blocks(self):
        evidence = sample()
        evidence["checks"] = []
        self.assertFalse(judge(FakeClient(evidence=evidence)).advisory_clear)

    def test_unprotected_main_blocks(self):
        evidence = sample()
        evidence["main"]["protected"] = False
        self.assertFalse(judge(FakeClient(evidence=evidence)).advisory_clear)

    def test_wrong_head_sha_blocks(self):
        self.assertFalse(judge(sha="c" * 40).advisory_clear)

    def test_stacked_pr_is_not_main_premerge(self):
        evidence = sample()
        evidence["pr"]["base"]["ref"] = "omega/ui-security"
        self.assertIn("STACKED_PR_NOT_MAIN_ACCEPTANCE",
                      judge(FakeClient(evidence=evidence)).blockers)

    def test_failed_runner_job_blocks(self):
        evidence = sample()
        evidence["runs"][0]["conclusion"] = "failure"
        self.assertFalse(judge(FakeClient(evidence=evidence)).advisory_clear)

    def test_human_review_for_source_code_required(self):
        evidence = sample()
        evidence["files"][0]["filename"] = "src/auth.py"
        self.assertFalse(judge(FakeClient(evidence=evidence)).advisory_clear)

    def test_main_moved_during_evidence_read_blocks(self):
        class MovingClient(FakeClient):
            def _get(self, endpoint):
                value = super()._get(endpoint)
                if endpoint == "/branches/main":
                    value["commit"]["sha"] = "c" * 40
                return value
        self.assertFalse(judge(MovingClient()).advisory_clear)

    def test_pr_moved_during_evidence_read_blocks(self):
        class MovingClient(FakeClient):
            def _get(self, endpoint):
                value = super()._get(endpoint)
                if endpoint == "/pulls/65":
                    value["head"]["sha"] = "c" * 40
                return value
        self.assertFalse(judge(MovingClient()).advisory_clear)

    def test_policy_disabled_blocks_even_when_ci_green(self):
        p = protection()
        p["enforce_admins"]["enabled"] = False
        self.assertFalse(judge(FakeClient(policy=p)).advisory_clear)


if __name__ == "__main__":
    unittest.main()
