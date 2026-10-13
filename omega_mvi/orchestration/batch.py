"""Data-only, one-command, multiple-fixture orchestration.

This is NOT a live agent dispatcher: never take tool handlers, URLs, scripts,
Python source or MCP transports from the owner command or output. The four
trusted callbacks below only return prevalidated literal fixture dictionaries.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Event
from typing import Any
from uuid import UUID

from .offline import (
    Denied, FixtureTool, OfflineMcpFixtureRegistry, OfflineReport, OfflineTask,
    run_offline,
)

_BINDINGS = {
    "plan": ("fixture.plan", "sandbox/planner", "rag:read"),
    "apply": ("fixture.apply", "sandbox/builder", "repository:read"),
    "test": ("fixture.test", "sandbox/tester", "inventory:read"),
    "audit": ("fixture.audit", "sandbox/auditor", "pr:read"),
}
_PHASES = tuple(_BINDINGS)
_RESULT_CODES = frozenset({"ok", "retryable"})


@dataclass(frozen=True)
class OfflineCommand:
    """Owner is a synthetic label, never an authenticated principal."""
    command: str
    trace_id: UUID
    owner: str
    children: tuple[OfflineTask, ...]
    total_budget_minor: int
    total_step_limit: int
    deadline_utc: datetime

    def __post_init__(self):
        if type(self.command) is not str or self.command != "inspect":
            raise Denied("COMMAND_NOT_ALLOWLISTED")
        if not isinstance(self.trace_id, UUID) or type(self.children) is not tuple:
            raise Denied("INVALID_COMMAND")
        if type(self.total_budget_minor) is not int or not 0 <= self.total_budget_minor <= 10000:
            raise Denied("INVALID_AGGREGATE_BUDGET")
        if type(self.total_step_limit) is not int or not 1 <= self.total_step_limit <= 100:
            raise Denied("INVALID_AGGREGATE_STEPS")
        if (not isinstance(self.deadline_utc, datetime) or
                self.deadline_utc.tzinfo is None or
                self.deadline_utc.utcoffset().total_seconds() != 0):
            raise Denied("INVALID_AGGREGATE_DEADLINE")
        if not 1 <= len(self.children) <= 4:
            raise Denied("INVALID_CHILD_COUNT")
        seen = set()
        for child in self.children:
            if (not isinstance(child, OfflineTask) or child.owner != self.owner or
                    child.trace_id != self.trace_id or child.task_id in seen):
                raise Denied("CHILD_OWNERSHIP_OR_ID_DENIED")
            seen.add(child.task_id)


@dataclass(frozen=True)
class OfflineCommandReport:
    trace_id: UUID
    status: str
    reason: str
    completed: int
    total_steps: int
    simulated_cost_minor: int
    reports: tuple[OfflineReport, ...]
    production_authorized: bool = False


def _validated_scripts(scripts: Any, n_children: int):
    """Freeze *only* literal outcome enums, with no caller functions."""
    if type(scripts) is not tuple or len(scripts) != n_children:
        raise Denied("INVALID_SCRIPT_SHAPE")
    frozen = []
    for script in scripts:
        if type(script) is not dict or not set(script).issubset(_PHASES):
            raise Denied("INVALID_SCRIPT_SHAPE")
        frozen_script = {}
        for phase in _PHASES:
            values = script.get(phase, ("ok",))
            if (type(values) is not tuple or not 1 <= len(values) <= 11 or
                    any(type(value) is not str or value not in _RESULT_CODES for value in values)):
                raise Denied("INVALID_SCRIPT_RESULT")
            frozen_script[phase] = values
        frozen.append(frozen_script)
    return tuple(frozen)


def _fixture_registry(script):
    """Trusted, static-code closures: no user-provided executable handlers."""
    reg = OfflineMcpFixtureRegistry()
    for phase, (name, boundary, scope) in _BINDINGS.items():
        outcomes = script[phase]
        call_count = [0]

        def safe_literal_handler(_context, *, outcomes=outcomes, call_count=call_count):
            index = call_count[0]
            call_count[0] += 1
            if index >= len(outcomes):
                # Missing expected test data must not become an implicit success.
                return {"result_code": "script_exhausted", "artifact_ref": "",
                        "checked": False}
            return {"result_code": outcomes[index], "artifact_ref": "synthetic://validated",
                    "checked": True}

        reg.register(phase, FixtureTool(name, boundary, scope, 1, safe_literal_handler))
    return reg


def simulate_offline_command(command: OfflineCommand, *,
                             scripts: tuple[dict[str, tuple[str, ...]], ...] | None = None,
                             cancelled: Event | None = None) -> OfflineCommandReport:
    """Run up to four separate mock tasks with global synthetic cost/step caps.

    Sequential and offline by design. Never calls a real tool or mutates the
    PostgreSQL task state machine. This is evidence of a fixture contract ONLY.
    """
    if not isinstance(command, OfflineCommand):
        raise Denied("OFFLINE_COMMAND_REQUIRED")
    if scripts is None:
        scripts = tuple({} for _ in command.children)
    safe_scripts = _validated_scripts(scripts, len(command.children))
    cancellation = cancelled if cancelled is not None else Event()
    if not isinstance(cancellation, Event):
        raise Denied("INVALID_STOP_CONTROL")

    cost = steps = completed = 0
    results = []

    def finish(status, reason):
        return OfflineCommandReport(command.trace_id, status, reason, completed,
                                    steps, cost, tuple(results))

    for task, script in zip(command.children, safe_scripts):
        if cancellation.is_set():
            return finish("CANCELLED", "CANCEL_REQUESTED")
        if datetime.now(timezone.utc) >= command.deadline_utc:
            return finish("DENIED", "GLOBAL_DEADLINE_EXPIRED")
        remaining_steps = command.total_step_limit - steps
        remaining_cost = command.total_budget_minor - cost
        if remaining_steps <= 0:
            return finish("DENIED", "GLOBAL_STEP_LIMIT")
        if remaining_cost < 4:
            # Each complete fixture cycle costs four minor units.
            return finish("DENIED", "GLOBAL_SIMULATED_BUDGET")
        narrowed = replace(task, max_steps=min(task.max_steps, remaining_steps),
                           budget_limit_minor=min(task.budget_limit_minor, remaining_cost),
                           deadline_utc=min(task.deadline_utc, command.deadline_utc))
        report = run_offline(narrowed, _fixture_registry(script), cancelled=cancellation)
        results.append(report)
        steps += report.steps
        cost += report.simulated_cost_minor
        if report.status != "SIMULATED_SUCCEEDED":
            return finish("DENIED" if report.status != "CANCELLED" else "CANCELLED",
                          report.reason)
        completed += 1
    return finish("SIMULATED_SUCCEEDED", "ALL_FIXTURE_CHILDREN_COMPLETE")
