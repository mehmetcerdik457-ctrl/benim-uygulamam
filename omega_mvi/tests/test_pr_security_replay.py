"""Synthetic durability/duplicate/race tests; no GitHub calls or real secrets."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import os
import unittest

from omega_mvi.pr_security.webhook import SignedWebhookEvidence, REPOSITORY
from omega_mvi.pr_security.replay import SQLiteDeliveryReplayStore, ReplayDenied

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


if __name__ == "__main__":
    unittest.main()
