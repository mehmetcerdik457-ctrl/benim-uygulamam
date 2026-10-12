"""OMEGA-055/058/059/084/085: inert offline orchestration contract.

NOT an MCP network client, production runner, real approver, or trusted identity.
Only explicit synthetic fixtures can be dispatched; there are no network or
filesystem write operations. State/events are in-memory test evidence only.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event
from time import monotonic
from typing import Callable, Mapping
from uuid import UUID
import re

_READ_SCOPES = frozenset({"repository:read", "inventory:read", "rag:read", "pr:read"})
# A different fixed boundary for every fixture. The agent cannot choose these.
_BINDINGS = {
    "plan": ("fixture.plan", "sandbox/planner", "rag:read"),
    "apply": ("fixture.apply", "sandbox/builder", "repository:read"),
    "test": ("fixture.test", "sandbox/tester", "inventory:read"),
    "audit": ("fixture.audit", "sandbox/auditor", "pr:read"),
}
_REF = re.compile(r"synthetic://[a-z0-9][a-z0-9-]{0,39}\Z", re.ASCII)
_OWNER = re.compile(r"[A-Za-z0-9_-]{1,128}\Z", re.ASCII)


class Denied(PermissionError):
    """A non-sensitive policy reason; never append attacker-controlled text."""


@dataclass(frozen=True)
class OfflineTask:
    task_id: UUID
    owner: str
    trace_id: UUID
    permissions: frozenset[str]
    budget_limit_minor: int
    deadline_utc: datetime
    max_steps: int = 12
    max_failures: int = 1
    max_retries: int = 1
    max_duration_seconds: int = 30

    def __post_init__(self):
        if not isinstance(self.task_id, UUID) or not isinstance(self.trace_id, UUID):
            raise Denied("INVALID_TASK_ID")
        if not isinstance(self.owner, str) or _OWNER.fullmatch(self.owner) is None:
            raise Denied("INVALID_OWNER")
        if type(self.permissions) is not frozenset or not self.permissions.issubset(_READ_SCOPES):
            raise Denied("INVALID_SCOPES")
        for key, low, high in (("budget_limit_minor", 0, 1_000_000_000),
                               ("max_steps", 1, 100), ("max_failures", 0, 10),
                               ("max_retries", 0, 10), ("max_duration_seconds", 1, 3600)):
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise Denied("INVALID_LIMITS")
        if (not isinstance(self.deadline_utc, datetime) or
                self.deadline_utc.tzinfo is None or
                self.deadline_utc.utcoffset() != timedelta(0)):
            raise Denied("INVALID_DEADLINE")


@dataclass(frozen=True)
class FixtureTool:
    """Registered by trusted test harness code; NEVER populated by an LLM."""
    name: str
    trust_domain: str
    required_scope: str
    simulated_cost_minor: int
    handler: Callable[[Mapping[str, object]], Mapping[str, object]]


class OfflineMcpFixtureRegistry:
    """MCP-shaped adapter contract; no MCP transport or external tool calls."""
    def __init__(self):
        self._tools = {}

    def register(self, phase: str, tool: FixtureTool):
        expected = _BINDINGS.get(phase)
        if (expected is None or not isinstance(tool, FixtureTool) or
                (tool.name, tool.trust_domain, tool.required_scope) != expected or
                type(tool.simulated_cost_minor) is not int or
                not 0 <= tool.simulated_cost_minor <= 1_000_000_000 or
                not callable(tool.handler) or phase in self._tools):
            raise Denied("TOOL_REGISTRATION_DENIED")
        self._tools[phase] = tool

    def get(self, phase: str) -> FixtureTool:
        if phase not in self._tools:
            raise Denied("TOOL_NOT_REGISTERED")
        return self._tools[phase]


def _validate_untrusted_output(value):
    # No arbitrary model/tool text, URLs, instructions, nested objects or keys
    # enter a subsequent stage. No exception messages appear in logs.
    if (type(value) is not dict or set(value) != {"result_code", "artifact_ref", "checked"} or
            type(value.get("result_code")) is not str or
            value["result_code"] not in ("ok", "retryable") or
            type(value.get("artifact_ref")) is not str or
            _REF.fullmatch(value["artifact_ref"]) is None or
            value.get("checked") is not True):
        raise Denied("UNTRUSTED_OUTPUT_REJECTED")
    return value["result_code"]


@dataclass(frozen=True)
class OfflineReport:
    task_id: UUID
    trace_id: UUID
    status: str
    reason: str
    steps: int
    failures: int
    retries: int
    simulated_cost_minor: int
    events: tuple[tuple[str, str], ...]
    production_authorized: bool = False


def run_offline(task: OfflineTask, registry: OfflineMcpFixtureRegistry, *,
                cancelled: Event | None = None,
                utc_now: Callable[[], datetime] | None = None,
                elapsed_clock: Callable[[], float] = monotonic) -> OfflineReport:
    """Fixed plan/apply/test/audit cycle with bounded, fail-closed retries.

    No persistent task state is mutated; does NOT call omega_transition and
    cannot evade the database's APPROVAL_PENDING->RUNNING denial.
    """
    if not isinstance(task, OfflineTask) or not isinstance(registry, OfflineMcpFixtureRegistry):
        raise Denied("OFFLINE_FIXTURE_REQUIRED")
    utc_now = utc_now or (lambda: datetime.now(timezone.utc))
    cancelled = cancelled or Event()
    started = elapsed_clock()
    steps = failures = retries = cost = 0
    events = []

    def report(status, reason):
        events.append((status, reason))
        return OfflineReport(task.task_id, task.trace_id, status, reason, steps,
                             failures, retries, cost, tuple(events))

    def guard():
        if cancelled.is_set():
            raise Denied("CANCEL_REQUESTED")
        now = utc_now()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise Denied("INVALID_CLOCK")
        if now >= task.deadline_utc:
            raise Denied("DEADLINE_EXPIRED")
        if elapsed_clock() - started >= task.max_duration_seconds:
            raise Denied("DURATION_LIMIT")
        if steps >= task.max_steps:
            raise Denied("STEP_LIMIT")

    while True:
        try:
            guard()
            for phase in ("plan", "apply", "test", "audit"):
                guard()
                tool = registry.get(phase)
                if tool.required_scope not in task.permissions:
                    raise Denied("SCOPE_DENIED")
                if cost + tool.simulated_cost_minor > task.budget_limit_minor:
                    raise Denied("SIMULATED_BUDGET_LIMIT")
                try:
                    # Only non-identifying fixture metadata reaches each adapter.
                    result = tool.handler({"phase": phase, "attempt": retries})
                except Exception:
                    raise Denied("TOOL_FAILURE") from None
                # Distinguish cancellation from timeout; never count a
                # callback result as completed if a stop arrived mid-call.
                if cancelled.is_set():
                    raise Denied("CANCEL_REQUESTED")
                if elapsed_clock() - started >= task.max_duration_seconds:
                    raise Denied("DURATION_LIMIT")
                if utc_now() >= task.deadline_utc:
                    raise Denied("DEADLINE_EXPIRED")
                outcome = _validate_untrusted_output(result)
                steps += 1
                cost += tool.simulated_cost_minor
                events.append((phase.upper(), "FIXTURE_RESULT_VALIDATED"))
                if outcome == "retryable":
                    failures += 1
                    if phase not in ("test", "audit"):
                        raise Denied("UNEXPECTED_RETRY")
                    if failures > task.max_failures:
                        raise Denied("FAILURE_LIMIT")
                    if retries >= task.max_retries:
                        raise Denied("RETRY_LIMIT")
                    retries += 1
                    events.append(("RETRY", "BOUNDED_SYNTHETIC_RETRY"))
                    break
            else:
                return report("SIMULATED_SUCCEEDED", "FOUR_PHASE_FIXTURE_ONLY")
        except Denied as exc:
            code = str(exc)
            return report("CANCELLED" if code == "CANCEL_REQUESTED" else "DENIED", code)
