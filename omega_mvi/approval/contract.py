"""Offline-only owner approval contract.

IMPORTANT: This module does NOT authenticate a real owner or authorize
execution. Authentication must come from a trusted, separately deployed
identity provider, and production decisions must be atomically verified and
consumed INSIDE PostgreSQL. The real execution gate stays disabled.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID

class ApprovalUnavailable(PermissionError):
    pass

@dataclass(frozen=True)
class Principal:
    subject: str
    issuer: str
    verified_at: datetime

@dataclass(frozen=True)
class Intent:
    task_id: UUID
    actor: str
    action: str
    resource: str
    scope: str

@dataclass(frozen=True)
class Decision:
    decision_id: UUID
    principal: Principal
    intent: Intent
    expires_at: datetime

def require_live_verified_owner(_principal, _intent, _decision):
    """Fail closed until signed identities + PostgreSQL atomic ledger exist."""
    raise ApprovalUnavailable("owner identity and durable atomic approval verification not provisioned")

class FakeApprovalLedger:
    """UNIT TEST ONLY. Never import into an API, job runner, or agent tool."""
    def __init__(self):
        self._lock=Lock()
        self._used=set()

    def consume_for_test(self, decision, trusted_fixture_principal, actual_intent, now):
        if not isinstance(decision,Decision) or not isinstance(now,datetime):
            raise ApprovalUnavailable("invalid decision")
        with self._lock:  # one-process fake for contract/replay tests; NOT a DB transaction
            if decision.decision_id in self._used:
                raise ApprovalUnavailable("replay denied")
            if decision.principal != trusted_fixture_principal:
                raise ApprovalUnavailable("principal mismatch")
            if decision.intent != actual_intent or decision.intent.actor != trusted_fixture_principal.subject:
                raise ApprovalUnavailable("task/actor/action/resource/scope mismatch")
            if now.tzinfo is None or decision.expires_at.tzinfo is None:
                raise ApprovalUnavailable("timezone required")
            if decision.expires_at <= now or decision.principal.verified_at > now:
                raise ApprovalUnavailable("expired or invalid identity")
            if decision.principal.issuer != "synthetic-test-idp":
                raise ApprovalUnavailable("test fixture issuer mismatch")
            self._used.add(decision.decision_id)
            return True
