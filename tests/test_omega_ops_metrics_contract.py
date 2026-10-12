"""OMEGA-092: synthetic telemetry schema, privacy/cardinality/age negative tests."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from omega_ops_metrics_contract import BOUNDS, validate_synthetic_samples

NOW = 2000000000


def fixture():
    return [{"name": name, "value": 2, "observed_at": NOW - 10,
             "origin": "synthetic-disposable-only"} for name in BOUNDS]


class SyntheticTelemetryContract(unittest.TestCase):
    def test_complete_private_free_sample_set(self):
        r = validate_synthetic_samples(fixture(), NOW)
        self.assertEqual(r["fixture"], "VALID_SYNTHETIC_ONLY")
        self.assertFalse(r["grafana_accepted"])

    def test_missing_metric_refused(self):
        self.assertEqual(validate_synthetic_samples(fixture()[:-1], NOW)["fixture"], "BLOCKED")

    def test_duplicate_metric_refused(self):
        data = fixture()
        data[-1] = dict(data[0])
        self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")

    def test_no_owner_or_secret_labels(self):
        data = fixture()
        data[0]["owner"] = "sensitive-unknown-owner"
        self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")
        self.assertNotIn("sensitive", str(validate_synthetic_samples(data, NOW)))

    def test_stale_and_future_samples_refused(self):
        for timestamp in (NOW - 121, NOW + 1):
            data = fixture()
            data[0]["observed_at"] = timestamp
            self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")

    def test_wrong_origin_rejected(self):
        data = fixture()
        data[0]["origin"] = "production"
        self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")

    def test_nonfinite_values_rejected(self):
        for number in (float("nan"), float("inf"), float("-inf")):
            data = fixture()
            data[0]["value"] = number
            self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")

    def test_negative_and_overflow_values_rejected(self):
        for number in (-1, 10**25, 10**1000):
            data = fixture()
            data[0]["value"] = number
            self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")

    def test_boolean_value_not_numeric_evidence(self):
        data = fixture()
        data[0]["value"] = True
        self.assertEqual(validate_synthetic_samples(data, NOW)["fixture"], "BLOCKED")

    def test_clock_missing_or_invalid(self):
        for clock in (None, True, -1, "tomorrow"):
            self.assertEqual(validate_synthetic_samples(fixture(), clock)["fixture"], "BLOCKED")

    def test_even_valid_fixture_never_accepts_real_grafana(self):
        self.assertFalse(validate_synthetic_samples(fixture(), NOW)["grafana_accepted"])


if __name__ == "__main__":
    unittest.main()
