"""OMEGA-090 negative release-gate tests: fixture-only, no GitHub/API writes."""
import copy
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from omega_ops_release_gate import REQUIRED, compare_untrusted_summaries


def sample(sha_char):
    return {
        "sha": sha_char * 40, "scope": "disposable-synthetic-ci",
        "checks": {
            name: {"conclusion": "success", "passed": 5, "failed": 0, "skipped": 0}
            for name in REQUIRED
        },
    }


class FailClosedReleaseGate(unittest.TestCase):
    def setUp(self):
        self.previous = sample("a")
        self.next = sample("b")

    def assess(self):
        return compare_untrusted_summaries(self.previous, self.next)

    def test_comparison_does_not_unfreeze(self):
        result = self.assess()
        self.assertEqual(result["comparison"], "COMPARABLE_UNTRUSTED")
        self.assertFalse(result["release_authorized"])
        self.assertEqual(result["reasons"], [])

    def test_missing_baseline_evidence_rejected(self):
        self.previous["checks"].pop("privacy_guard")
        self.assertEqual(self.assess()["comparison"], "BLOCKED")

    def test_missing_candidate_runner_host_rejected(self):
        self.next["checks"].pop("runner_host_acceptance")
        self.assertIn("runner_host_acceptance_candidate_missing_or_unacceptable",
                      self.assess()["reasons"])

    def test_failed_check_blocks(self):
        self.next["checks"]["postgres_restore"]["conclusion"] = "failure"
        self.assertEqual(self.assess()["comparison"], "BLOCKED")

    def test_skipped_check_blocks(self):
        self.next["checks"]["execution_denial"]["skipped"] = 1
        self.assertEqual(self.assess()["comparison"], "BLOCKED")

    def test_counts_cannot_regress(self):
        self.next["checks"]["regression_suite"]["passed"] = 4
        self.assertIn("regression_suite_test_count_regressed", self.assess()["reasons"])

    def test_invalid_sha_blocks(self):
        self.next["sha"] = "../unexpected-ref"
        self.assertIn("candidate_sha_invalid", self.assess()["reasons"])

    def test_identical_sha_is_not_independent_comparison(self):
        self.next["sha"] = self.previous["sha"]
        self.assertIn("same_sha_not_a_comparison", self.assess()["reasons"])

    def test_wrong_scope_rejected(self):
        self.next["scope"] = "production"
        self.assertIn("candidate_scope_invalid", self.assess()["reasons"])

    def test_boolean_cannot_forge_test_counts(self):
        self.next["checks"]["privacy_guard"]["passed"] = True
        self.assertEqual(self.assess()["comparison"], "BLOCKED")

    def test_untrusted_text_never_echoed(self):
        payload = "PRIVATE_DATA_DO_NOT_LOG"
        self.next["scope"] = payload
        self.next["checks"]["privacy_guard"]["conclusion"] = payload
        self.assertNotIn(payload, str(self.assess()))

    def test_cli_remains_frozen_without_authenticated_source(self):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/omega_ops_release_gate.py")],
                             capture_output=True, text=True, check=True)
        self.assertIn("FROZEN_NO_AUTHENTICATED_OWNER_OR_PROVENANCE", run.stdout)
        self.assertIn("OMEGA_RELEASE_AUTHORIZED=FALSE", run.stdout)


if __name__ == "__main__":
    unittest.main()
