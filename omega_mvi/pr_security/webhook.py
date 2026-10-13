"""Pure, non-authorizing GitHub webhook verifier (no listener or Check publisher).

Do not mistake a valid HMAC for a current PR state or publication authority.
Caller needs a durable atomic delivery-ID replay registry and a fresh GitHub GET.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from typing import Mapping
from uuid import UUID

REPOSITORY = "mehmetcerdik457-ctrl/benim-uygulamam"
HEX_SHA = re.compile(r"[0-9a-f]{40}\Z")
HEX_SIGNATURE = re.compile(r"sha256=[0-9a-f]{64}\Z")
LIMIT_BYTES = 1024 * 1024
ALLOWED_ACTIONS = frozenset({"opened", "reopened", "synchronize", "ready_for_review"})


class UntrustedWebhook(ValueError):
    """Invalid webhook; never include signed body, signature or secret."""


@dataclass(frozen=True)
class SignedWebhookEvidence:
    repository: str
    issue_or_pr_number: int
    head_sha: str
    base_sha: str
    delivery_id: str
    installation_id: int
    action: str
    authenticated: bool = True
    can_publish_checks: bool = False
    blockers: tuple[str, ...] = (
        "DURABLE_ATOMIC_REPLAY_RESERVATION_NOT_PROVEN",
        "FRESH_PR_AND_CHECKS_NOT_REVALIDATED",
        "CHECKS_PUBLISHER_APP_NOT_CONFIGURED",
        "OWNER_RULESET_APPROVAL_MISSING",
    )


def verify_pr_webhook(
    *,
    body: bytes,
    headers: Mapping[str, str],
    webhook_secret: bytes,
    expected_installation_id: int,
    expected_repository_id: int,
    expected_pr_number: int,
    expected_head_sha: str,
    expected_base_sha: str,
) -> SignedWebhookEvidence:
    """Authenticate bytes and bind event identities, never publish or grant access."""
    if not isinstance(body, bytes) or not body or len(body) > LIMIT_BYTES:
        raise UntrustedWebhook("Invalid webhook body")
    if not isinstance(webhook_secret, bytes) or len(webhook_secret) < 16:
        raise UntrustedWebhook("Webhook signing key is missing or invalid")
    if not isinstance(headers, Mapping):
        raise UntrustedWebhook("Webhook headers missing")
    lower = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise UntrustedWebhook("Invalid webhook header")
        canonical = key.lower()
        if canonical in lower:
            raise UntrustedWebhook("Ambiguous repeated webhook header")
        lower[canonical] = value
    provided = lower.get("x-hub-signature-256")
    if not isinstance(provided, str) or not HEX_SIGNATURE.fullmatch(provided):
        raise UntrustedWebhook("SHA-256 webhook signature required")
    expected = "sha256=" + hmac.new(webhook_secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise UntrustedWebhook("Webhook signature mismatch")
    if lower.get("x-github-event") != "pull_request":
        raise UntrustedWebhook("Unsupported event")
    delivery = lower.get("x-github-delivery")
    if not isinstance(delivery, str):
        raise UntrustedWebhook("Missing delivery ID")
    try:
        UUID(delivery)
    except (ValueError, AttributeError) as exc:
        raise UntrustedWebhook("Invalid delivery ID") from exc
    if (type(expected_installation_id) is not int or expected_installation_id <= 0
            or type(expected_repository_id) is not int or expected_repository_id <= 0
            or type(expected_pr_number) is not int or expected_pr_number <= 0):
        raise UntrustedWebhook("Trusted IDs are not configured")
    if (not isinstance(expected_head_sha, str) or not HEX_SHA.fullmatch(expected_head_sha)
            or not isinstance(expected_base_sha, str) or not HEX_SHA.fullmatch(expected_base_sha)):
        raise UntrustedWebhook("Pinned SHAs invalid")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise UntrustedWebhook("Invalid JSON data") from exc
    if not isinstance(payload, dict):
        raise UntrustedWebhook("Invalid webhook JSON object")
    repo = payload.get("repository")
    pr = payload.get("pull_request")
    installation = payload.get("installation")
    if not all(isinstance(obj, dict) for obj in (repo, pr, installation)):
        raise UntrustedWebhook("Missing signed payload identity")
    if (repo.get("full_name") != REPOSITORY
            or repo.get("id") != expected_repository_id
            or installation.get("id") != expected_installation_id):
        raise UntrustedWebhook("Signed repository or installation mismatch")
    if (payload.get("number") != expected_pr_number
            or pr.get("number") != expected_pr_number
            or payload.get("action") not in ALLOWED_ACTIONS):
        raise UntrustedWebhook("Unexpected PR/action")
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise UntrustedWebhook("Missing signed PR refs")
    if head.get("sha") != expected_head_sha or base.get("sha") != expected_base_sha:
        raise UntrustedWebhook("Webhook PR/ref mismatch")
    return SignedWebhookEvidence(
        repository=REPOSITORY,
        issue_or_pr_number=expected_pr_number,
        head_sha=expected_head_sha, base_sha=expected_base_sha,
        installation_id=expected_installation_id, delivery_id=delivery,
        action=payload["action"],
    )
