"""No-network, synthetic HMAC webhook tests (no signing key committed)."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import hmac
import json
import unittest

from omega_mvi.pr_security.webhook import (
    UntrustedWebhook, verify_pr_webhook, REPOSITORY,
)

HEAD = "a" * 40
BASE = "b" * 40
SYNTHETIC_KEY = b"local-synthetic-only-signing-material"
DELIVERY = "44f77612-7d94-4dbc-ab8e-0cf55a15a001"


def event():
    return {
        "action": "synchronize",
        "number": 100,
        "repository": {"id": 991, "full_name": REPOSITORY},
        "installation": {"id": 123},
        "pull_request": {"number": 100, "head": {"sha": HEAD},
                         "base": {"sha": BASE}},
    }


def verify(payload=None, **overrides):
    body = json.dumps(event() if payload is None else payload).encode("utf-8")
    sig = "sha256=" + hmac.new(SYNTHETIC_KEY, body, hashlib.sha256).hexdigest()
    headers = {
        "X-Hub-Signature-256": sig,
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": DELIVERY,
    }
    headers.update(overrides.pop("headers", {}))
    values = dict(
        body=body, headers=headers, webhook_secret=SYNTHETIC_KEY,
        expected_installation_id=123, expected_repository_id=991,
        expected_pr_number=100, expected_head_sha=HEAD,
        expected_base_sha=BASE,
    )
    values.update(overrides)
    return verify_pr_webhook(**values)


class WebhookContracts(unittest.TestCase):
    def test_valid_signed_event_is_non_authoritative(self):
        r = verify()
        self.assertTrue(r.authenticated)
        self.assertFalse(r.can_publish_checks)
        self.assertIn("DURABLE_ATOMIC_REPLAY_RESERVATION_NOT_PROVEN", r.blockers)

    def test_frozen_receipt_cannot_grant_authority(self):
        with self.assertRaises(FrozenInstanceError):
            verify().can_publish_checks = True

    def test_tampered_bytes_denied(self):
        body = json.dumps(event()).encode("utf-8") + b" "
        with self.assertRaises(UntrustedWebhook): verify(body=body)

    def test_missing_signature_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(headers={"X-Hub-Signature-256": ""})

    def test_legacy_sha1_not_accepted(self):
        with self.assertRaises(UntrustedWebhook):
            verify(headers={"X-Hub-Signature-256": "sha1=" + "a" * 40})

    def test_wrong_event_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(headers={"X-GitHub-Event": "push"})

    def test_bad_delivery_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(headers={"X-GitHub-Delivery": "not-a-guid"})

    def test_duplicate_case_insensitive_header_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(headers={"x-hub-signature-256": "sha256=" + "0" * 64})

    def test_wrong_repository_denied(self):
        p = event(); p["repository"]["full_name"] = "other/repo"
        with self.assertRaises(UntrustedWebhook): verify(p)

    def test_wrong_repository_id_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(expected_repository_id=999)

    def test_wrong_installation_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(expected_installation_id=999)

    def test_wrong_pr_number_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(expected_pr_number=999)

    def test_wrong_head_sha_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(expected_head_sha="0" * 40)

    def test_wrong_base_sha_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(expected_base_sha="0" * 40)

    def test_unsupported_action_denied(self):
        p = event(); p["action"] = "closed"
        with self.assertRaises(UntrustedWebhook):
            verify(p)

    def test_synthetic_signed_body_over_limit_denied(self):
        with self.assertRaises(UntrustedWebhook):
            verify(body=b"a" * (1024 * 1024 + 1))

    def test_missing_installation_denied(self):
        p = event(); del p["installation"]
        with self.assertRaises(UntrustedWebhook): verify(p)

    def test_no_check_write_method_exposed(self):
        from omega_mvi.pr_security import webhook
        self.assertFalse(hasattr(webhook, "create_check_run"))
        self.assertFalse(hasattr(webhook, "publish_check"))


if __name__ == "__main__":
    unittest.main()
