"""Offline negative tests. Fake backends NEVER count as real inference."""
import asyncio
import pytest

from omega_mvi.model_adapter.router import (
    Completion, InferenceFailed, ModelProfile, ModelRouter, PermanentModelError,
    Privacy, RouteDenied, RouteRequest, TransientModelError,
)


class Stub:
    def __init__(self, model, *, faults=(), duration=0, usage_offset=0, token_error=False):
        self.name = model
        self.faults = list(faults)
        self.duration = duration
        self.usage_offset = usage_offset
        self.token_error = token_error
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self.cancelled = 0

    def count_prompt_tokens(self, prompt, system_prompt):
        if self.token_error:
            raise ValueError("no tokenizer")
        return len(prompt.split()) + (len(system_prompt.split()) if system_prompt else 0) + 2

    async def generate(self, request, *, max_output_tokens):
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.faults:
                raise self.faults.pop(0)
            await asyncio.sleep(self.duration)
            return Completion(self.name, "offline fixture", self.count_prompt_tokens(request.prompt, request.system_prompt), 2+self.usage_offset)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        finally:
            self.active -= 1


def profile(name="local-a", **kw):
    base = dict(name=name, tasks=frozenset({"code", "chat"}), max_privacy=Privacy.RESTRICTED,
                context_tokens=1024, output_tokens=50, quality_by_task={"chat": 80, "code": 80},
                measured_p95_latency_ms=100, timeout_ms=500, concurrency=1, max_retries=1)
    base.update(kw)
    return ModelProfile(**base)


def request(**kw):
    base = dict(task="chat", prompt="hello world", max_input_tokens=40,
                max_output_tokens=5, max_total_tokens=45, deadline_ms=2000)
    base.update(kw)
    return RouteRequest(**base)


def run(coro):
    return asyncio.run(coro)


def test_routing_local_highest_verified_quality():
    a, b = Stub("local-a"), Stub("local-b")
    router = ModelRouter([(profile("local-a", quality_by_task={"chat": 50}), a),
                          (profile("local-b", quality_by_task={"chat": 90}), b)])
    assert run(router.generate(request())).model == "local-b"
    assert a.calls == 0


def test_confidential_never_falls_back_to_public():
    first, unsafe = Stub("private", faults=[TransientModelError("no")]*2), Stub("public")
    router = ModelRouter([(profile("private"), first),
                          (profile("public", max_privacy=Privacy.PUBLIC), unsafe)])
    with pytest.raises(InferenceFailed):
        run(router.generate(request(privacy=Privacy.RESTRICTED)))
    assert unsafe.calls == 0


def test_transient_retry_bounded_then_safe_fallback():
    a, b = Stub("a", faults=[TransientModelError("down")]*2), Stub("b")
    router = ModelRouter([(profile("a", quality_by_task={"chat": 99}), a),
                          (profile("b", quality_by_task={"chat": 80}), b)])
    assert run(router.generate(request())).model == "b"
    assert (a.calls, b.calls) == (2, 1)


def test_timeout_cancelled_backend_then_fallback():
    a, b = Stub("a", duration=.2), Stub("b")
    router = ModelRouter([(profile("a", timeout_ms=10, max_retries=0), a),
                          (profile("b", quality_by_task={"chat": 60}), b)])
    assert run(router.generate(request())).model == "b"
    assert a.cancelled == 1


def test_actual_task_cancellation_does_not_fallback():
    async def action():
        a, b = Stub("a", duration=1), Stub("b")
        router = ModelRouter([(profile("a"), a), (profile("b"), b)])
        task = asyncio.create_task(router.generate(request()))
        await asyncio.sleep(.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert a.cancelled == 1 and b.calls == 0
    run(action())


def test_queue_concurrency_bound():
    async def action():
        a = Stub("local-a", duration=.03)
        router = ModelRouter([(profile(concurrency=1), a)])
        results = await asyncio.gather(*(router.generate(request()) for _ in range(6)))
        assert len(results) == 6 and a.max_active == 1
    run(action())


@pytest.mark.parametrize("changes", [
    {"max_total_tokens": 2}, {"max_output_tokens": 51},
    {"max_input_tokens": 1}, {"min_quality": 95},
    {"max_p95_latency_ms": 50}, {"allowed_models": frozenset({"other"})},
    {"max_external_cost_microusd": 1},
])
def test_token_quality_cost_and_latency_constraints_fail_closed(changes):
    a = Stub("local-a")
    with pytest.raises(RouteDenied):
        run(ModelRouter([(profile(), a)]).generate(request(**changes)))
    assert a.calls == 0


def test_missing_tokenizer_fails_closed():
    a = Stub("local-a", token_error=True)
    with pytest.raises(RouteDenied):
        run(ModelRouter([(profile(), a)]).generate(request()))
    assert a.calls == 0


def test_unexpected_token_usage_blocks_fallback():
    a, b = Stub("a", usage_offset=99), Stub("b")
    router = ModelRouter([(profile("a"), a), (profile("b"), b)])
    with pytest.raises(InferenceFailed, match="token usage"):
        run(router.generate(request()))
    assert b.calls == 0


def test_permanent_error_does_not_retry_or_fallback():
    a, b = Stub("a", faults=[PermanentModelError("do not expose")]), Stub("b")
    router = ModelRouter([(profile("a"), a), (profile("b"), b)])
    with pytest.raises(InferenceFailed) as exc:
        run(router.generate(request()))
    assert "do not expose" not in str(exc.value)
    assert (a.calls, b.calls) == (1, 0)


def test_never_auto_register_paid_or_remote_models():
    with pytest.raises(ValueError, match="local"):
        ModelRouter([(profile(deployment="remote"), Stub("local-a"))])
    with pytest.raises(ValueError, match="local"):
        ModelRouter([(profile(external_cost_microusd=1), Stub("local-a"))])


def test_missing_measured_sla_refuses_estimates():
    a = Stub("local-a")
    with pytest.raises(RouteDenied):
        run(ModelRouter([(profile(measured_p95_latency_ms=None), a)]).generate(
            request(max_p95_latency_ms=500)))


def test_global_concurrency_across_distinct_models():
    async def action():
        a, b = Stub("a", duration=.03), Stub("b", duration=.03)
        router = ModelRouter([(profile("a"), a), (profile("b"), b)], global_concurrency=1)
        await asyncio.gather(router.generate(request(allowed_models=frozenset({"a"}))),
                             router.generate(request(allowed_models=frozenset({"b"}))))
        assert a.calls == b.calls == 1
    run(action())


def test_global_concurrency_rejects_unsafe_limit():
    with pytest.raises(ValueError):
        ModelRouter([], global_concurrency=0)
