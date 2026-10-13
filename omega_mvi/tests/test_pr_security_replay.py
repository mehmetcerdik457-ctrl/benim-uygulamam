"""Synthetic durability/duplicate/race tests; no GitHub calls or real secrets."""
from dataclasses import replace
from pathlib import Path
import json
import hashlib
import hmac
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import os
import unittest

from omega_mvi.pr_security.webhook import SignedWebhookEvidence, REPOSITORY
from omega_mvi.pr_security.replay import SQLiteDeliveryReplayStore, ReplayDenied, authenticate_and_reserve
from omega_mvi.pr_security.webhook import UntrustedWebhook

DELIVERY = "8cb7eec3-f0d1-4589-9cda-042da2f01234"


def receipt(delivery=DELIVERY):
    return SignedWebhookEvidence(
        repository=REPOSITORY,
        issue_or_pr_number=65,
        head_sha="a" * 40,
        base_sha="b" * 40,
        delivery_id=delivery,
        installation_id=123,
        action="synchronize",
    )


class ReplayStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "webhook-replay.sqlite3")

    def test_first_signed_delivery_is_reserved(self):
        self.assertIsNone(SQLiteDeliveryReplayStore(self.path).reserve(receipt()))
        self.assertTrue(Path(self.path).is_file())

    def test_duplicate_delivery_is_rejected(self):
        store = SQLiteDeliveryReplayStore(self.path)
        store.reserve(receipt())
        with self.assertRaises(ReplayDenied):
            store.reserve(receipt())

    def test_duplicate_across_new_process_like_store_instance_is_rejected(self):
        SQLiteDeliveryReplayStore(self.path).reserve(receipt())
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore(self.path).reserve(receipt())

    def test_same_id_different_head_is_rejected(self):
        store = SQLiteDeliveryReplayStore(self.path)
        store.reserve(receipt())
        with self.assertRaises(ReplayDenied):
            store.reserve(replace(receipt(), head_sha="c" * 40))

    def test_other_guid_is_permitted(self):
        store = SQLiteDeliveryReplayStore(self.path)
        store.reserve(receipt())
        store.reserve(receipt("8cb7eec3-f0d1-4589-9cda-042da2f01235"))

    def test_concurrent_reservations_only_one_wins(self):
        def attempt(_):
            try:
                SQLiteDeliveryReplayStore(self.path).reserve(receipt())
                return True
            except ReplayDenied:
                return False
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(attempt, range(4)))
        self.assertEqual(sum(results), 1)

    def test_reject_relative_path(self):
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore("relative.sqlite")

    def test_reject_memory_path(self):
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore(":memory:")

    def test_reject_missing_parent(self):
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore(str(Path(self.tmp.name) / "missing" / "db.sqlite"))

    def test_refuse_existing_symlink(self):
        target = Path(self.tmp.name) / "real.sqlite"
        symlink = Path(self.tmp.name) / "alias.sqlite"
        target.touch()
        symlink.symlink_to(target)
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore(str(symlink))

    def test_non_receipt_refused(self):
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore(self.path).reserve(object())

    def test_refuse_bogus_delivery_id(self):
        with self.assertRaises(ReplayDenied):
            SQLiteDeliveryReplayStore(self.path).reserve(receipt("not-a-guid"))

    def test_db_is_file_and_writes_no_credentials(self):
        SQLiteDeliveryReplayStore(self.path).reserve(receipt())
        raw = Path(self.path).read_bytes()
        self.assertNotIn(b"X-Hub-Signature", raw)
        self.assertNotIn(b"Authorization", raw)

    def test_deleted_parent_causes_denial(self):
        path = str(Path(self.tmp.name) / "other" / "replay.db")
        parent = Path(path).parent
        parent.mkdir()
        store = SQLiteDeliveryReplayStore(path)
        parent.rmdir()
        with self.assertRaises(ReplayDenied):
            store.reserve(receipt())




def synthetic_webhook_args():
    key = b"synthetic-only-webhook-key-material"
    payload = {
        "action": "synchronize", "number": 65,
        "repository": {"id": 1001, "full_name": REPOSITORY},
        "installation": {"id": 222},
        "pull_request": {
            "number": 65, "head": {"sha": "a" * 40}, "base": {"sha": "b" * 40},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    sig = "sha256=" + hmac.new(key, body, hashlib.sha256).hexdigest()
    return {
        "body": body,
        "headers": {
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": DELIVERY,
        },
        "webhook_secret": key,
        "expected_installation_id": 222,
        "expected_repository_id": 1001,
        "expected_pr_number": 65,
        "expected_head_sha": "a" * 40,
        "expected_base_sha": "b" * 40,
    }


class AuthenticatedReservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteDeliveryReplayStore(str(Path(self.tmp.name) / "replay.sqlite"))

    def test_authenticated_delivery_creates_non_authorizing_receipt(self):
        signed = authenticate_and_reserve(self.store, **synthetic_webhook_args())
        self.assertTrue(signed.authenticated)
        self.assertFalse(signed.can_publish_checks)

    def test_second_delivery_same_guid_is_rejected(self):
        authenticate_and_reserve(self.store, **synthetic_webhook_args())
        with self.assertRaises(ReplayDenied):
            authenticate_and_reserve(self.store, **synthetic_webhook_args())

    def test_modified_payload_cannot_skip_signature_check(self):
        args = synthetic_webhook_args()
        args["body"] = args["body"] + b" "
        with self.assertRaises(UntrustedWebhook):
            authenticate_and_reserve(self.store, **args)
        # Bad signature was rejected before durable reservation.
        authenticate_and_reserve(self.store, **synthetic_webhook_args())

    def test_wrong_head_does_not_consume_delivery(self):
        args = synthetic_webhook_args()
        args["expected_head_sha"] = "c" * 40
        with self.assertRaises(UntrustedWebhook):
            authenticate_and_reserve(self.store, **args)
        authenticate_and_reserve(self.store, **synthetic_webhook_args())

    def test_missing_real_store_rejected(self):
        with self.assertRaises(ReplayDenied):
            authenticate_and_reserve(object(), **synthetic_webhook_args())

    def test_authenticated_delivery_same_id_rejected_after_new_store_object(self):
        args = synthetic_webhook_args()
        authenticate_and_reserve(self.store, **args)
        other = SQLiteDeliveryReplayStore(str(Path(self.tmp.name) / "replay.sqlite"))
        with self.assertRaises(ReplayDenied):
            authenticate_and_reserve(other, **args)


if __name__ == "__main__":
    unittest.main()
