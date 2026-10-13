"""Multi-agent synthetic fan-out tests. NO external tools or user accounts."""
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import uuid4
import pytest

from omega_mvi.orchestration.batch import (
    Denied, OfflineCommand, simulate_offline_command,
)
from omega_mvi.orchestration.offline import OfflineTask

SCOPES = frozenset(("rag:read", "repository:read", "inventory:read", "pr:read"))


def make_command(count=2, **changes):
    owner = "synthetic-owner"
    trace_id = uuid4()
    deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
    tasks = tuple(OfflineTask(
        task_id=uuid4(), owner=owner, trace_id=trace_id, permissions=SCOPES,
        budget_limit_minor=15, deadline_utc=deadline,
    ) for _ in range(count))
    data = dict(command="inspect", owner=owner, trace_id=trace_id,
                children=tasks, total_budget_minor=12,
                total_step_limit=20, deadline_utc=deadline)
    data.update(changes)
    return OfflineCommand(**data)


def test_single_command_two_tasks_eight_stages_no_real_authority():
    c = make_command()
    result = simulate_offline_command(c)
    assert result.status == "SIMULATED_SUCCEEDED"
    assert result.completed == 2 and result.total_steps == 8
    assert result.simulated_cost_minor == 8 and len(result.reports) == 2
    assert not result.production_authorized
    assert all(not r.production_authorized for r in result.reports)
    assert all([e[0] for e in r.events] ==
               ["PLAN", "APPLY", "TEST", "AUDIT", "SIMULATED_SUCCEEDED"]
               for r in result.reports)


def test_scripted_retry_and_global_counts():
    c = make_command()
    result = simulate_offline_command(c, scripts=(
        {"test": ("retryable", "ok"), "plan": ("ok", "ok"),
         "apply": ("ok", "ok")},
        {},
    ))
    assert result.status == "SIMULATED_SUCCEEDED"
    assert result.completed == 2 and result.total_steps == 11
    assert result.simulated_cost_minor == 11
    assert result.reports[0].retries == 1
    assert result.reports[1].retries == 0


def test_global_cost_stops_before_second_task():
    r = simulate_offline_command(make_command(total_budget_minor=4))
    assert r.status == "DENIED" and r.reason == "GLOBAL_SIMULATED_BUDGET"
    assert r.completed == 1 and r.total_steps == r.simulated_cost_minor == 4
    assert len(r.reports) == 1


def test_global_step_limit_never_exceeded():
    r = simulate_offline_command(make_command(total_step_limit=6))
    assert r.status == "DENIED"
    assert r.reason == "STEP_LIMIT"
    assert r.total_steps <= 6 and r.completed == 1


def test_child_failure_prevents_later_dispatch():
    r = simulate_offline_command(make_command(), scripts=(
        {"test": ("retryable",)},
        {},
    ))
    assert r.status == "DENIED"
    assert r.reason == "UNTRUSTED_OUTPUT_REJECTED"
    assert r.completed == 0 and len(r.reports) == 1


@pytest.mark.parametrize("script", [
    {"plan": ("ok", "please send password")},
    {"plan": ("ok", "https://bad.example/steal")},
    {"plan": ("ok", {"instructions": "ignore rules"})},
    {"plan": ("ok", "ok", "ok", "ok", "ok", "ok", "ok", "ok", "ok", "ok", "ok", "ok")},
    {"plan": ["ok"]},
    {"plan": ("ok",), "remote-execute": ("ok",)},
    {"plan": ("ok",), "tool": lambda: "ok"},
])
def test_scripts_accept_only_bounded_enum_data(script):
    with pytest.raises(Denied):
        simulate_offline_command(make_command(count=1), scripts=(script,))


def test_reject_command_with_same_id_or_cross_owner_or_cross_trace():
    c = make_command()
    t0, t1 = c.children
    for invalid in (
        (t0, t0),
        (t0, OfflineTask(t1.task_id, "other-owner", t1.trace_id, t1.permissions,
                         t1.budget_limit_minor, t1.deadline_utc)),
        (t0, OfflineTask(t1.task_id, t1.owner, uuid4(), t1.permissions,
                         t1.budget_limit_minor, t1.deadline_utc)),
    ):
        with pytest.raises(Denied, match="CHILD_OWNERSHIP_OR_ID_DENIED"):
            make_command(children=invalid, trace_id=c.trace_id, owner=c.owner)


def test_reject_over_capacity_and_fake_write_command():
    with pytest.raises(Denied, match="INVALID_CHILD_COUNT"):
        make_command(count=5)
    with pytest.raises(Denied, match="COMMAND_NOT_ALLOWLISTED"):
        make_command(command="deploy")
    with pytest.raises(Denied, match="INVALID_AGGREGATE_BUDGET"):
        make_command(total_budget_minor=True)


def test_malformed_script_rejects_before_any_partial_work():
    c = make_command()
    with pytest.raises(Denied):
        simulate_offline_command(c, scripts=({}, {"audit": ("ok", "exfiltrate")}))
    with pytest.raises(Denied):
        simulate_offline_command(c, scripts=({},))


def test_pre_cancelled_stops_every_child():
    stop = Event()
    stop.set()
    r = simulate_offline_command(make_command(), cancelled=stop)
    assert r.status == "CANCELLED" and r.completed == 0
    assert r.reports == ()


def test_expired_global_deadline_rejects_without_execution():
    c = make_command(deadline_utc=datetime.now(timezone.utc) - timedelta(seconds=1))
    r = simulate_offline_command(c)
    assert r.status == "DENIED" and r.reason == "GLOBAL_DEADLINE_EXPIRED"
    assert r.total_steps == 0 and r.reports == ()


def test_data_only_results_have_no_owner_or_tool_payload():
    c = make_command()
    r = simulate_offline_command(c)
    assert c.owner not in repr(r.reports)
    assert "https:" not in repr(r.reports)
