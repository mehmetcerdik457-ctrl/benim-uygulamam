"""Disposable PostgreSQL MOCK-only billing ledger. No real purchases or money."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re

MOCK_ONLY = "MOCK_ONLY"
KINDS = frozenset({"MOCK_PURCHASED","MOCK_RENEWED","MOCK_PENDING","MOCK_REFUNDED","MOCK_EXPIRED","MOCK_CANCELED"})
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")

class MockBillingError(ValueError):
    pass

class MockReplayConflict(MockBillingError):
    pass

def require_disposable_postgres(conn) -> None:
    """Deny queries outside the CI-only database, role and random test schema.

    This protects against an accidentally supplied production connection or
    a changed search_path. It is not a production-grade billing authorization
    mechanism and must not be used as one.
    """
    identity = conn.execute(
        "SELECT current_database(), current_user, current_schema()"
    ).fetchone()
    if (not identity or len(identity) != 3
            or identity[0] != "omega_mock"
            or identity[1] != "omega_mock"
            or not isinstance(identity[2], str)
            or not re.fullmatch(r"omega_mock_[0-9a-f]{32}", identity[2])):
        raise MockBillingError("not a disposable PostgreSQL CI test session")


@dataclass(frozen=True)
class MockEvent:
    event_id: str
    owner_id: str
    user_id: str
    product_id: str
    kind: str

def apply_mock_event(conn, event: MockEvent, *, actor_owner: str,
                     mode: str = MOCK_ONLY, fault_after_insert: bool = False) -> str:
    """Can modify ONLY a disposable test schema, not real-world entitlements."""
    if mode != MOCK_ONLY or not isinstance(event, MockEvent):
        raise MockBillingError("production billing disabled")
    require_disposable_postgres(conn)
    for value in (event.event_id, event.owner_id, event.user_id, event.product_id):
        if not isinstance(value,str) or not ID.fullmatch(value):
            raise MockBillingError("invalid mock identifier")
    if event.kind not in KINDS:
        raise MockBillingError("not a mock-only purchase event")
    if actor_owner != event.owner_id:
        raise PermissionError("wrong mock owner")
    data = dict(event_id=event.event_id, owner_id=event.owner_id,
                user_id=event.user_id, product_id=event.product_id, kind=event.kind)
    fp = hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    with conn.transaction():
        inserted = conn.execute(
            """INSERT INTO sandbox_billing_events
                (provider,event_id,owner_id,user_id,product_id,kind,fingerprint)
                VALUES ('local-mock',%s,%s,%s,%s,%s,%s)
                ON CONFLICT (provider,event_id) DO NOTHING RETURNING event_id""",
            (event.event_id,event.owner_id,event.user_id,event.product_id,event.kind,fp),
        ).fetchone()
        if inserted is None:
            previous = conn.execute(
                "SELECT fingerprint FROM sandbox_billing_events WHERE provider='local-mock' AND event_id=%s",
                (event.event_id,),
            ).fetchone()
            if previous is None or previous[0] != fp:
                raise MockReplayConflict("event ID collision/payload mismatch")
            return "IDEMPOTENT_REPLAY"
        if fault_after_insert:
            raise RuntimeError("deliberate test fault")
        if event.kind == "MOCK_PENDING":
            return "PENDING_NO_GRANT"
        state = "ACTIVE" if event.kind in ("MOCK_PURCHASED","MOCK_RENEWED") else "INACTIVE"
        conn.execute(
            """INSERT INTO sandbox_entitlements
                (owner_id,user_id,product_id,state,last_event_id)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (owner_id,user_id,product_id)
                DO UPDATE SET state=EXCLUDED.state,last_event_id=EXCLUDED.last_event_id""",
            (event.owner_id,event.user_id,event.product_id,state,event.event_id),
        )
        return "MOCK_ACTIVE" if state == "ACTIVE" else "MOCK_INACTIVE"

def mock_entitlement_state(conn, owner_id: str, user_id: str, product_id: str) -> str | None:
    require_disposable_postgres(conn)
    for item in (owner_id,user_id,product_id):
        if not isinstance(item,str) or not ID.fullmatch(item):
            raise MockBillingError("invalid mock identifier")
    row = conn.execute(
        "SELECT state FROM sandbox_entitlements WHERE owner_id=%s AND user_id=%s AND product_id=%s",
        (owner_id,user_id,product_id)
    ).fetchone()
    return row[0] if row else None
