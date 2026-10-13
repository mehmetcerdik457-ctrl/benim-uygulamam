"""Bounded cooperative cancellation guard for injected local inference coroutines.

An uncooperative task may remain alive after this function returns. Callers must
quarantine their router and use a killable isolated worker for production.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class BackendUnresponsive(Exception):
    """An inference task violated cancellation integrity (no detail leakage)."""


def _drain(task: asyncio.Task[object]) -> None:
    """Consume late task exceptions without emitting prompts/provider details."""
    if task.done() and not task.cancelled():
        try:
            task.exception()
        except BaseException:
            pass


async def _stop(task: asyncio.Task[T], grace_s: float, quarantine: Callable[[], None]) -> bool:
    """Request cancellation; return True only if task acknowledged cancellation."""
    task.cancel()
    try:
        done, _ = await asyncio.wait({task}, timeout=grace_s)
    except asyncio.CancelledError:
        quarantine()
        task.add_done_callback(_drain)
        raise
    if task in done and task.cancelled():
        return True
    quarantine()
    task.add_done_callback(_drain)
    return False


async def bounded_inference(
    invocation: Awaitable[T], *, timeout_s: float, cancel_grace_s: float,
    quarantine: Callable[[], None],
) -> T:
    """Bound one attempt even if backend swallows CancelledError.

    Timeout with cooperative cancellation -> TimeoutError (eligible for retry).
    Timeout with ignored cancellation -> BackendUnresponsive + quarantine.
    Parent task cancellation -> cancellation propagated with bounded cleanup.
    """
    task = asyncio.create_task(invocation)
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout_s)
    except asyncio.CancelledError:
        await _stop(task, cancel_grace_s, quarantine)
        raise
    if task in done:
        return await task
    if await _stop(task, cancel_grace_s, quarantine):
        raise asyncio.TimeoutError()
    raise BackendUnresponsive("local backend failed cancellation integrity")
