"""Synthetic, offline Copilot handoff tests. No Copilot call/assignment."""
from dataclasses import FrozenInstanceError
import dataclasses
import unittest

from omega_mvi.copilot_delegation import HandoffDenied, plan_handoff, REPOSITORY

VALID = dict(
    repository=REPOSITORY,
    issue_number=49,
    trace_id="20f7c02e-8e91-49a0-98ec-e1f3a8e01111",
    base_ref="omega/integration-20261011",
    pinned_base_sha="a" * 40,
    budget_cents=0,
    deadline_utc="2026-10-12T08:00:00Z",
)


def plan(**changes):
    args = dict(VALID)
    args.update(changes)
    return plan_handoff(**args)


class CopilotHandoffTests(unittest.TestCase):
    def test_intent_is_blocked_even_with_valid_metadata(self):
        r = plan()
        self.assertTrue(r.dry_run)
        self.assertFalse(r.can_dispatch)
        self.assertEqual(r.status, "BLOCKED")
        self.assertIn("COPILOT_ENTITLEMENT_UNKNOWN", r.blockers)

    def test_no_prompt_or_token_in_receipt(self):
        r = plan()
        self.assertNotIn("prompt", dataclasses.asdict(r))
        self.assertNotIn("token", dataclasses.asdict(r))

    def test_receipt_cannot_be_mutated(self):
        with self.assertRaises(FrozenInstanceError):
            plan().can_dispatch = True

    def test_wrong_repository_denied(self):
        with self.assertRaises(HandoffDenied): plan(repository="outsider/repo")

    def test_invalid_issue_denied(self):
        for issue in (False, 0, -1, "49"):
            with self.subTest(issue=issue), self.assertRaises(HandoffDenied):
                plan(issue_number=issue)

    def test_invalid_trace_id_denied(self):
        for value in ("", "made-up", " "):
            with self.subTest(value=value), self.assertRaises(HandoffDenied):
                plan(trace_id=value)

    def test_arbitrary_branch_denied(self):
        for ref in ("refs/heads/main", "../main", "other/repo", "omega/../main", ""):
            with self.subTest(ref=ref), self.assertRaises(HandoffDenied):
                plan(base_ref=ref)

    def test_invalid_base_sha_denied(self):
        for sha in ("a" * 39, "0" * 64, "g" * 40):
            with self.subTest(sha=sha), self.assertRaises(HandoffDenied):
                plan(pinned_base_sha=sha)

    def test_budget_must_not_be_negative_or_boolean(self):
        for budget in (True, -1, 2.4):
            with self.subTest(budget=budget), self.assertRaises(HandoffDenied):
                plan(budget_cents=budget)

    def test_explicit_utc_deadline_required(self):
        for date in ("tomorrow", "2026-10-12T08:00:00", "2026-10-12T08:00:00+03:00"):
            with self.subTest(date=date), self.assertRaises(HandoffDenied):
                plan(deadline_utc=date)

    def test_does_not_expose_any_network_operations(self):
        from omega_mvi import copilot_delegation as module
        self.assertFalse(hasattr(module, "dispatch"))
        self.assertFalse(hasattr(module, "assign_issue"))
        self.assertFalse(hasattr(module, "send_request"))


if __name__ == "__main__":
    unittest.main()
