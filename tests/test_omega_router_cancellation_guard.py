"""Cancellation integrity tests: synthetic coroutines, no local model daemon."""
import asyncio
import time

import pytest

from omega_mvi.model_adapter.router import (
    Completion, InferenceFailed, ModelProfile, ModelRouter,
    Privacy, RouteDenied, RouteRequest,
)


def prof(name):
    return ModelProfile(
        name=name, tasks=frozenset({"chat"}), max_privacy=Privacy.RESTRICTED,
        context_tokens=64, output_tokens=8, quality_by_task={"chat": 80},
        timeout_ms=10, max_retries=0,
    )


def req():
    return RouteRequest(task="chat", prompt="synthetic", deadline_ms=200,
                        max_input_tokens=10, max_output_tokens=4, max_total_tokens=14)


class Mock:
    def __init__(self, name, *, delay=0):
        self.name = name
        self.delay = delay
        self.calls = 0
        self.cancelled = 0

    def count_prompt_tokens(self, prompt, system_prompt):
        return 2

    async def generate(self, request, *, max_output_tokens):
        self.calls += 1
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        return Completion(self.name, "fixture", 2, 1)


class Rogue(Mock):
    def __init__(self, name, release, reached):
        super().__init__(name)
        self.release, self.reached = release, reached

    async def generate(self, request, *, max_output_tokens):
        self.calls += 1
        self.reached.set()
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            await self.release.wait()  # deliberately swallows cancellation
        return Completion(self.name, "unsafe late", 2, 1)


def run(awaitable):
    return asyncio.run(awaitable)


def test_noncooperative_model_cannot_block_request_indefinitely():
    async def action():
        release, reached = asyncio.Event(), asyncio.Event()
        rogue, backup = Rogue("rogue", release, reached), Mock("backup")
        router = ModelRouter([(prof("rogue"), rogue), (prof("backup"), backup)],
                             cancel_grace_ms=15)
        start = time.monotonic()
        try:
            with pytest.raises(InferenceFailed, match="ignored timeout"):
                await router.generate(req())
            assert time.monotonic() - start < .5
            assert router._quarantined
            assert backup.calls == 0
            with pytest.raises(RouteDenied, match="quarantined"):
                await router.generate(req())
        finally:
            release.set()
            await asyncio.sleep(.01)
    run(action())


def test_parent_cancellation_is_bounded_and_quarantines_rogue():
    async def action():
        release, reached = asyncio.Event(), asyncio.Event()
        rogue = Rogue("rogue", release, reached)
        router = ModelRouter([(prof("rogue"), rogue)], cancel_grace_ms=15)
        task = asyncio.create_task(router.generate(req()))
        await reached.wait()
        task.cancel()
        try:
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, .5)
            assert router._quarantined
            assert router._inflight == 0
        finally:
            release.set()
            await asyncio.sleep(.01)
    run(action())


def test_cooperative_timeout_can_use_privacy_eligible_local_fallback():
    async def action():
        slow, backup = Mock("slow", delay=.2), Mock("backup")
        router = ModelRouter([(prof("slow"), slow), (prof("backup"), backup)],
                             cancel_grace_ms=50)
        result = await router.generate(req())
        assert result.model == "backup"
        assert slow.cancelled == 1
        assert not router._quarantined
    run(action())


@pytest.mark.parametrize("value", [0, -1, True, 5001, 2.5])
def test_cancel_grace_invalid_parameters_rejected(value):
    with pytest.raises(ValueError, match="cancellation grace"):
        ModelRouter([], cancel_grace_ms=value)


def test_router_defaults_to_unquarantined():
    router = ModelRouter([])
    assert not router._quarantined
