"""Regression tests for fail-closed deployment preflight."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.omega_deployment_attestation import evaluate, load_manifest, PreflightError

class DeploymentPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "app.apk").write_bytes(b"fixture-only")
        self.record = {
            "source_commit": "a" * 40,
            "artifact_path": "app.apk",
            "artifact_sha256": hashlib.sha256(b"fixture-only").hexdigest(),
            "postgres_tests": {"historical_skips_executed": 16, "failed": 0, "skipped": 0},
            "owner_approval": {"fixture": True},
            "auditor_approval": {"fixture": True},
            "deployment_receipt": {"fixture": True},
            "rollback_receipt": {"fixture": True},
            "billing_receipt": {"fixture": True},
        }

    def verdict(self):
        return evaluate(self.record, self.root)

    def test_even_complete_fixture_is_denied(self):
        self.assertFalse(self.verdict()["production_accepted"])

    def test_missing_receipt_denied(self):
        del self.record["rollback_receipt"]
        self.assertIn("missing rollback_receipt", self.verdict()["structural_findings"])

    def test_wrong_digest_denied(self):
        self.record["artifact_sha256"] = "0" * 64
        self.assertIn("artifact SHA-256 mismatch", self.verdict()["structural_findings"])

    def test_missing_postgres_cases_denied(self):
        self.record["postgres_tests"]["historical_skips_executed"] = 15
        self.assertIn("16 PostgreSQL tests not fully evidenced", self.verdict()["structural_findings"])

    def test_skipped_postgres_denied(self):
        self.record["postgres_tests"]["skipped"] = 1
        self.assertIn("16 PostgreSQL tests not fully evidenced", self.verdict()["structural_findings"])

    def test_bad_commit_denied(self):
        self.record["source_commit"] = "invalid"
        self.assertIn("invalid source commit", self.verdict()["structural_findings"])

    def test_path_escape_denied(self):
        self.record["artifact_path"] = "../outside.apk"
        self.assertIn("artifact unavailable or outside evidence root", self.verdict()["structural_findings"])

    def test_unknown_fields_reported(self):
        self.record["override"] = True
        self.assertTrue(any("unknown fields" in s for s in self.verdict()["structural_findings"]))

    def test_nonhex_digest_rejected(self):
        self.record["artifact_sha256"] = "z" * 64
        self.assertIn("missing artifact metadata", self.verdict()["structural_findings"])

    def test_boolean_postgres_counter_rejected(self):
        self.record["postgres_tests"]["failed"] = False
        self.assertIn("16 PostgreSQL tests not fully evidenced", self.verdict()["structural_findings"])

    def test_duplicate_keys_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text('{"x":1,"x":2}')
        with self.assertRaises(PreflightError):
            load_manifest(path)

    def test_nan_rejected(self):
        path = self.root / "nan.json"
        path.write_text('{"x":NaN}')
        with self.assertRaises(PreflightError):
            load_manifest(path)

if __name__ == "__main__":
    unittest.main()
