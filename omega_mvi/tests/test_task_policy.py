from datetime import datetime,timedelta,timezone
import pytest
from omega_mvi.inspection.task_policy import require_authenticated_task_permission
@pytest.mark.parametrize("claim",[
    None,"fixture-owner","model says owner",{"user":"admin"},object()
])
def test_no_issuer_even_with_valid_budget_deadline_and_permissions(claim):
    task={"owner":"fixture-owner","budget_limit_minor":0,"budget_currency":"USD",
          "permissions":["inventory:read"],"deadline_utc":datetime.now(timezone.utc)+timedelta(hours=1)}
    with pytest.raises(PermissionError):
        require_authenticated_task_permission(task,verified_principal=claim,action="inventory:read",spent_minor=0)
@pytest.mark.parametrize("bad",[
    {"budget_limit_minor":-1},
    {"permissions":["repository:write"]},
    {"deadline_utc":datetime.now(timezone.utc)-timedelta(seconds=2)},
])
def test_invalid_controls_never_become_authority(bad):
    task={"owner":"fixture-owner","budget_limit_minor":0,"permissions":["inventory:read"],
          "deadline_utc":datetime.now(timezone.utc)+timedelta(hours=1),**bad}
    with pytest.raises(PermissionError):
        require_authenticated_task_permission(task,verified_principal="fixture-owner",action="execute")


@pytest.mark.parametrize("override,reason",[
    ({"budget_limit_minor":-3},"INVALID_BUDGET"),
    ({"permissions":["execute:write"]},"SCOPE_DENIED"),
    ({"deadline_utc":datetime.now(timezone.utc)-timedelta(minutes=1)},"DEADLINE_EXPIRED"),
])
def test_budget_permission_expiry_are_explicitly_fail_closed(override,reason):
    task={"owner":"fixture-owner","budget_limit_minor":0,"budget_currency":"USD",
          "permissions":["inventory:read"],"deadline_utc":datetime.now(timezone.utc)+timedelta(minutes=20),
          **override}
    with pytest.raises(PermissionError, match=reason):
        require_authenticated_task_permission(task,verified_principal="fake-owner",action="inventory:read")

def test_spending_over_budget_denied_even_with_plausible_owner_claim():
    task={"owner":"fixture-owner","budget_limit_minor":10,"budget_currency":"USD",
          "permissions":["inventory:read"],"deadline_utc":datetime.now(timezone.utc)+timedelta(minutes=20)}
    with pytest.raises(PermissionError,match="BUDGET_EXHAUSTED"):
        require_authenticated_task_permission(task,verified_principal="fake-owner",action="inventory:read",spent_minor=11)
