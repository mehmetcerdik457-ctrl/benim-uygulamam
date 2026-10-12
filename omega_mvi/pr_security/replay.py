"""Durable, atomic, local-only GitHub webhook delivery replay reservation.

The reservation must happen AFTER HMAC verification and BEFORE any privileged
operation. A failed downstream operation must not silently release a delivery.
The store is not an HTTP server, webhook handler or GitHub Checks publisher.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
from uuid import UUID

from omega_mvi.pr_security.webhook import SignedWebhookEvidence


class ReplayDenied(RuntimeError):
    """Fail-closed persistence or duplicate-delivery rejection."""


class SQLiteDeliveryReplayStore:
    """Persistent single-writer transaction + unique delivery-ID constraint.

    The caller supplies an existing, non-symlink directory with controlled
    filesystem permissions. Intended for a single shared-disk deployment.
    Multi-host deployments require a separate transactional shared backend.
    """

    def __init__(self, database_path: str):
        if not isinstance(database_path, str) or not database_path:
            raise ReplayDenied("Explicit persistent database path is required")
        path = Path(database_path)
        if (not path.is_absolute() or path.name in ("", ".", "..")
                or "\x00" in database_path or database_path.startswith("file:")
                or path.is_symlink() or not path.parent.is_dir()):
            raise ReplayDenied("Unsafe or unavailable replay DB path")
        self._path = path

    def reserve(self, signed: SignedWebhookEvidence) -> None:
        """Exactly-once reservation attempt; never erase/rollback committed IDs."""
        if not isinstance(signed, SignedWebhookEvidence) or not signed.authenticated:
            raise ReplayDenied("Authenticated signed webhook evidence required")
        if signed.can_publish_checks:
            raise ReplayDenied("Invalid authority in signed evidence")
        try:
            normalized_id = str(UUID(signed.delivery_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ReplayDenied("Malformed delivery ID") from exc
        if normalized_id != signed.delivery_id.lower():
            raise ReplayDenied("Noncanonical delivery ID")
        if self._path.is_symlink() or not self._path.parent.is_dir():
            raise ReplayDenied("Replay DB path was changed")
        conn = None
        try:
            conn = sqlite3.connect(str(self._path), timeout=1.0, isolation_level=None)
            conn.execute("PRAGMA busy_timeout = 1000")
            conn.execute("PRAGMA synchronous = FULL")
            conn.execute("""CREATE TABLE IF NOT EXISTS webhook_delivery_reservations (
                delivery_id TEXT PRIMARY KEY NOT NULL,
                repository TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                head_sha TEXT NOT NULL
            ) WITHOUT ROWID""")
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "INSERT INTO webhook_delivery_reservations "
                "(delivery_id, repository, pr_number, head_sha) VALUES (?, ?, ?, ?)",
                (normalized_id, signed.repository, signed.issue_or_pr_number,
                 signed.head_sha),
            )
            if cursor.rowcount != 1:
                raise ReplayDenied("Delivery reservation was not recorded")
            conn.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            raise ReplayDenied("Duplicate webhook delivery") from exc
        except sqlite3.Error as exc:
            raise ReplayDenied("Replay DB unavailable: deny action") from exc
        finally:
            if conn is not None:
                if conn.in_transaction:
                    conn.rollback()
                conn.close()


def authenticate_and_reserve(
    store: SQLiteDeliveryReplayStore,
    *,
    body: bytes,
    headers: dict[str, str],
    webhook_secret: bytes,
    expected_installation_id: int,
    expected_repository_id: int,
    expected_pr_number: int,
    expected_head_sha: str,
    expected_base_sha: str,
) -> SignedWebhookEvidence:
    """One supported call path: signature -> signed metadata -> durable replay ID.

    This is NOT a GitHub webhook HTTP receiver, installation authentication,
    external side-effect, fresh SHA check or Checks publishing authority.
    """
    from omega_mvi.pr_security.webhook import verify_pr_webhook

    signed = verify_pr_webhook(
        body=body, headers=headers, webhook_secret=webhook_secret,
        expected_installation_id=expected_installation_id,
        expected_repository_id=expected_repository_id,
        expected_pr_number=expected_pr_number,
        expected_head_sha=expected_head_sha, expected_base_sha=expected_base_sha,
    )
    if not isinstance(store, SQLiteDeliveryReplayStore):
        raise ReplayDenied("Durable replay store is required")
    store.reserve(signed)
    return signed
