"""Strict negative tests for OMEGA-094 isolated Python-venv SBOM."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from omega_ops_sbom import inventory


class FakeDist:
    def __init__(self, name, version):
        self.metadata = {"Name": name}
        self.version = version


SHA = "a" * 40


class IsolatedSbomContract(unittest.TestCase):
    def test_minimal_cdx_and_scope(self):
        obj = inventory([FakeDist("FastAPI", "0.115.12"), FakeDist("httpx", "0.28.1")], SHA)
        self.assertEqual(obj["bomFormat"], "CycloneDX")
        self.assertEqual(obj["specVersion"], "1.5")
        self.assertEqual([x["name"] for x in obj["components"]], ["fastapi", "httpx"])
        self.assertEqual(obj["metadata"]["properties"][1]["value"], "isolated-ci-python-venv-only")
        self.assertNotIn("email", json.dumps(obj).lower())
        self.assertNotIn("/home/", json.dumps(obj))

    def test_order_does_not_change_serial(self):
        d = [FakeDist("httpx", "0.28.1"), FakeDist("FastAPI", "0.115.12")]
        self.assertEqual(inventory(d, SHA), inventory(list(reversed(d)), SHA))

    def test_duplicate_identical_package_collapses(self):
        obj = inventory([FakeDist("a_b", "1.0"), FakeDist("a-b", "1.0")], SHA)
        self.assertEqual(len(obj["components"]), 1)

    def test_mismatched_canonical_identity_rejected(self):
        with self.assertRaises(ValueError):
            inventory([FakeDist("pkg.a", "1"), FakeDist("pkg-a", "2")], SHA)

    def test_no_secret_string_in_name(self):
        for bad in ("token=abc123", "internal/private", "x\nnot-safe", "", "x" * 130):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    inventory([FakeDist(bad, "1.0")], SHA)

    def test_reject_arbitrary_version_metadata(self):
        for bad in ("1.0?auth=secret", "1.0\nleak", "../tmp", "", "1" * 130):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    inventory([FakeDist("lib", bad)], SHA)

    def test_sha_invalid(self):
        for sha in (None, "", "0" * 39, "g" * 40, 3):
            with self.assertRaises(ValueError):
                inventory([FakeDist("lib", "1.0")], sha)

    def test_empty_fails_closed(self):
        with self.assertRaises(ValueError):
            inventory([], SHA)

    def test_too_many_package_names_fails_closed(self):
        with self.assertRaises(ValueError):
            inventory([FakeDist(f"lib{i}", "1") for i in range(401)], SHA)

    def test_version_keeps_safe_epoch(self):
        obj = inventory([FakeDist("lib", "1!1.2+cpu")], SHA)
        self.assertEqual(obj["components"][0]["version"], "1!1.2+cpu")


if __name__ == "__main__":
    unittest.main()
