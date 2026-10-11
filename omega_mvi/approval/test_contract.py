"""MVI-03 unit tests only; fake approval IS NOT production acceptance."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from .contract import ApprovalUnavailable, Decision, FakeApprovalLedger, Intent, Principal, require_live_verified_owner

NOW=datetime(2026,10,11,tzinfo=timezone.utc)

def fixture_decision():
    person=Principal("test-owner","synthetic-test-idp",NOW-timedelta(minutes=1))
    intent=Intent(uuid4(),"test-owner","execute","synthetic-task","demo-only")
    return Decision(uuid4(),person,intent,NOW+timedelta(minutes=3))

def test_production_gate_fails_closed_even_with_valid_looking_decision():
    d=fixture_decision()
    with pytest.raises(ApprovalUnavailable):
        require_live_verified_owner(d.principal,d.intent,d)

def test_offline_fake_is_single_use():
    d=fixture_decision()
    ledger=FakeApprovalLedger()
    assert ledger.consume_for_test(d,d.principal,d.intent,NOW)
    with pytest.raises(ApprovalUnavailable):
        ledger.consume_for_test(d,d.principal,d.intent,NOW)

@pytest.mark.parametrize("change",["expired","different_task","wrong_actor","wrong_action","wrong_resource","wrong_scope","wrong_identity","forged_issuer"])
def test_offline_fake_rejects_binding_or_expiry_mismatch(change):
    d=fixture_decision()
    principal=d.principal
    intent=d.intent
    now=NOW
    if change=="expired": now=d.expires_at
    elif change=="different_task": intent=replace(intent,task_id=uuid4())
    elif change=="wrong_actor": intent=replace(intent,actor="other-actor")
    elif change=="wrong_action": intent=replace(intent,action="delete")
    elif change=="wrong_resource": intent=replace(intent,resource="another-task")
    elif change=="wrong_scope": intent=replace(intent,scope="all-repositories")
    elif change=="wrong_identity": principal=replace(principal,subject="other-owner")
    else: d=replace(d,principal=replace(principal,issuer="untrusted-agent"))
    with pytest.raises(ApprovalUnavailable):
        FakeApprovalLedger().consume_for_test(d,principal,intent,now)
