"""Negative-only synthetic tests; no network, models, or owner data."""
import asyncio
import pytest
from omega_mvi.model_adapter.router import (
    Completion, InferenceFailed, ModelProfile, ModelRouter, Privacy, RouteDenied,
    RouteRequest, TransientModelError,
)


def profile(name="local", **updates):
    data = dict(name=name, tasks=frozenset({"chat"}), max_privacy=Privacy.RESTRICTED,
                context_tokens=100, output_tokens=10, quality_by_task={"chat": 75},
                concurrency=1, timeout_ms=1000, max_retries=0)
    data.update(updates)
    return ModelProfile(**data)


def request(**updates):
    data = dict(task="chat", prompt="synthetic", max_input_tokens=10,
                max_output_tokens=2, max_total_tokens=12, deadline_ms=500)
    data.update(updates)
    return RouteRequest(**data)


class Backend:
    def __init__(self, name="local", delay=0, answer=None):
        self.name = name
        self.delay = delay
        self.answer = answer
        self.calls = 0
        self.cancelled = 0

    def count_prompt_tokens(self, prompt, system_prompt):
        return 2

    async def generate(self, req, *, max_output_tokens):
        self.calls += 1
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        return self.answer or Completion(self.name, "fixture", 2, 1)


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("bad", [
    {"privacy": -1}, {"privacy": 3}, {"privacy": "PUBLIC"},
    {"min_quality": True}, {"min_quality": 101},
    {"max_output_tokens": True}, {"max_total_tokens": 0},
    {"deadline_ms": 0}, {"max_p95_latency_ms": False},
    {"allowed_models": {"local"}},
    {"max_external_cost_microusd": 0.5},
    {"system_prompt": 7},
])
def test_request_untyped_or_unsafe_rejected_before_model(bad):
    backend = Backend()
    with pytest.raises(RouteDenied):
        run(ModelRouter([(profile(), backend)]).generate(request(**bad)))
    assert backend.calls == 0


@pytest.mark.parametrize("bad", [
    {"max_privacy": 3}, {"concurrency": True},
    {"max_retries": 3}, {"timeout_ms": False},
    {"measured_p95_latency_ms": 0},
    {"quality_by_task": {"chat": True}},
    {"quality_by_task": {"chat": 101}},
    {"quality_by_task": {"unknown": 80}},
    {"tasks": {"chat"}},
    {"external_cost_microusd": -1},
])
def test_bad_model_registration_rejected(bad):
    with pytest.raises(ValueError):
        ModelRouter([(profile(**bad), Backend())])


def test_mutable_quality_registry_metadata_is_copied():
    mutable = {"chat": 80}
    backend = Backend()
    router = ModelRouter([(profile(quality_by_task=mutable), backend)])
    mutable["chat"] = 0
    assert run(router.generate(request(min_quality=70))).model == "local"


def test_queue_limit_refuses_before_backend_and_recovers_after_cancellation():
    async def action():
        backend = Backend(delay=2)
        router = ModelRouter([(profile(), backend)], max_inflight_requests=2)
        first = asyncio.create_task(router.generate(request(deadline_ms=3000)))
        while backend.calls < 1:
            await asyncio.sleep(.001)
        second = asyncio.create_task(router.generate(request(deadline_ms=3000)))
        await asyncio.sleep(.01)
        with pytest.raises(RouteDenied, match="admission capacity"):
            await router.generate(request(deadline_ms=3000))
        assert backend.calls == 1
        for task in (first, second):
            task.cancel()
        for task in (first, second):
            with pytest.raises(asyncio.CancelledError):
                await task
        assert backend.cancelled == 1
        quick = ModelRouter([(profile(), Backend())])
        assert (await quick.generate(request())).text == "fixture"
        assert router._inflight == 0  # internal post-cancel counter invariant
    run(action())


def test_queue_waiting_considered_in_per_model_timeout():
    async def action():
        backend = Backend(delay=.2)
        router = ModelRouter([(profile(timeout_ms=35), backend)], max_inflight_requests=2)
        tasks = [asyncio.create_task(router.generate(request(deadline_ms=350))) for _ in range(2)]
        for task in tasks:
            with pytest.raises(InferenceFailed):
                await task
        assert router._inflight == 0
    run(action())


@pytest.mark.parametrize("completion", [
    Completion("other", "fixture", 2, 1),
    Completion("local", "fixture", 2, 99),
    Completion("local", "fixture", 2, True),
    Completion("local", "fixture", 2, 1, float("nan")),
    Completion("local", "fixture", 2, 1, -2.0),
    Completion("local", 42, 2, 1),
])
def test_malformed_completion_prevents_silent_fallback(completion):
    first, second = Backend(answer=completion), Backend(name="second")
    router = ModelRouter([(profile(), first), (profile("second"), second)])
    with pytest.raises(InferenceFailed, match="mismatch"):
        run(router.generate(request()))
    assert second.calls == 0


def test_permitted_fallback_on_bounded_transient_only():
    class Offline:
        def count_prompt_tokens(self, prompt, system_prompt):
            return 2

        async def generate(self, request, *, max_output_tokens):
            raise TransientModelError("fixture")

    b = Backend("backup")
    router = ModelRouter([(profile("primary"), Offline()), (profile("backup"), b)])
    assert run(router.generate(request())).model == "backup"
    assert b.calls == 1


def test_queue_settings_rejected_if_unbounded():
    with pytest.raises(ValueError):
        ModelRouter([], max_inflight_requests=0)
    with pytest.raises(ValueError):
        ModelRouter([], max_inflight_requests=1025)


def test_backend_ignoring_cancel_cannot_return_late_success_or_fallback():
    class IgnoresCancellation(Backend):
        async def generate(self, req, *, max_output_tokens):
            self.calls += 1
            try:
                await asyncio.sleep(.10)
            except asyncio.CancelledError:
                await asyncio.sleep(.02)
            return Completion(self.name, "unsafe-late", 2, 1)

    first, safe = IgnoresCancellation(), Backend(name="safe")
    router = ModelRouter([(profile(timeout_ms=5), first), (profile("safe"), safe)])
    with pytest.raises(InferenceFailed, match="ignored timeout"):
        run(router.generate(request()))
    assert safe.calls == 0
