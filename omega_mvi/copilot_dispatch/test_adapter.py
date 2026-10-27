"""Offline contract checks. Never submits a remote task."""
import unittest
from unittest.mock import patch
from omega_mvi.copilot_dispatch.adapter import REPO, ROLES, dispatch, validate

def manifest():
    return {"repository": REPO, "pinned_sha": "a" * 40,
            "branch": "omega/test", "owner_dispatch_approved": True,
            "tasks": [{"role": role, "issue": i + 100,
                       "approved": True, "prompt": "Review the bounded OMEGA issue safely."}
                      for i, role in enumerate(ROLES)]}

class DispatchContract(unittest.TestCase):
    def test_preview_no_network(self):
        with patch("omega_mvi.copilot_dispatch.adapter.api", side_effect=AssertionError("NETWORK")):
            self.assertEqual(dispatch(manifest())["sent"], 0)

    def test_requires_user_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "USER_TOKEN_REQUIRED"):
                dispatch(manifest(), execute=True, journal_path="/tmp/unused.sqlite")

    def test_rejects_unapproved_task(self):
        m = manifest()
        m["tasks"][0]["approved"] = False
        with self.assertRaises(ValueError):
            validate(m)

    def test_rejects_duplicate_issue(self):
        m = manifest()
        m["tasks"][0]["issue"] = m["tasks"][1]["issue"]
        with self.assertRaises(ValueError):
            validate(m)

    def test_rejects_malformed_task(self):
        m = manifest()
        m["tasks"][0] = None
        with self.assertRaises(ValueError):
            validate(m)

if __name__ == "__main__":
    unittest.main()
