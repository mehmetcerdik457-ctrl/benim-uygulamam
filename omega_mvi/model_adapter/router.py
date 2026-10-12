"""Offline-first model routing POLICY, not a live model or network integration.

Injected backends must supply accurate tokenizer/chat-template counts, enforce
output limits, and cooperate with cancellation. This router is for a *single*
asyncio event loop; its semaphore is not a process-wide resource limit.
"""
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field, replace
from enum import IntEnum
from types import MappingProxyType
from typing import Mapping, Protocol


class Privacy(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class RouteDenied(Exception):
    """No eligible model or no admission capacity; no inference initiated."""


class TransientModelError(Exception):
    """Retryable LOCAL failure with no partial output or external side effect."""


class PermanentModelError(Exception):
    """Non-retryable refusal or invalid request."""


class InferenceFailed(Exception):
    """Model error: intentionally excludes provider output and prompts."""


@dataclass(frozen=True)
class RouteRequest:
    task: str
    prompt: str
    privacy: Privacy = Privacy.RESTRICTED
    system_prompt: str | None = None
    min_quality: int = 0
    max_input_tokens: int = 4096
    max_output_tokens: int = 256
    max_total_tokens: int = 4096
    deadline_ms: int = 10000
    max_p95_latency_ms: int | None = None
    max_external_cost_microusd: int = 0
    allowed_models: frozenset[str] | None = None


@dataclass(frozen=True)
class ModelProfile:
    name: str
    tasks: frozenset[str]
    max_privacy: Privacy
    context_tokens: int
    output_tokens: int
    quality_by_task: Mapping[str, int] = field(default_factory=dict)
    measured_p95_latency_ms: int | None = None
    external_cost_microusd: int = 0
    deployment: str = "local"
    concurrency: int = 1
    timeout_ms: int = 3000
    max_retries: int = 1


@dataclass(frozen=True)
class Completion:
    model: str
    text: str
    prompt_tokens: int
    completion_tokens: int
    ttft_ms: float | None = None


class AsyncBackend(Protocol):
    def count_prompt_tokens(self, prompt: str, system_prompt: str | None) -> int:
        """Exact tokenizer+chat-template count; synchronous call must be bounded."""
        ...

    async def generate(self, request: RouteRequest, *, max_output_tokens: int) -> Completion:
        """Must enforce output cap before response, cancellation and no partial retries."""
        ...


def _bounded_int(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _privacy(value: object) -> bool:
    return type(value) is Privacy


class ModelRouter:
    """Policy gate + bounded scheduling; does not start/own an inference engine."""

    def __init__(
        self,
        registrations: list[tuple[ModelProfile, AsyncBackend]],
        *,
        global_concurrency: int = 1,
        max_inflight_requests: int = 8,
    ) -> None:
        if not _bounded_int(global_concurrency, 1, 32):
            raise ValueError("invalid global concurrency")
        if not _bounded_int(max_inflight_requests, global_concurrency, 1024):
            raise ValueError("invalid admission capacity")
        self._global_semaphore = asyncio.Semaphore(global_concurrency)
        self._max_inflight_requests = max_inflight_requests
        self._inflight = 0
        self._models: list[tuple[ModelProfile, AsyncBackend, asyncio.Semaphore]] = []
        names: set[str] = set()
        for profile, backend in registrations:
            if (not isinstance(profile.name, str) or not 1 <= len(profile.name) <= 128
                or not profile.name.strip() or profile.name in names):
                raise ValueError("duplicate/invalid model name")
            if profile.deployment != "local" or not _bounded_int(profile.external_cost_microusd, 0, 0):
                raise ValueError("only zero-external-cost local backends allowed")
            if (not _privacy(profile.max_privacy) or type(profile.tasks) is not frozenset
                or not profile.tasks or any(type(t) is not str or not t for t in profile.tasks)
                or not _bounded_int(profile.context_tokens, 1, 10_000_000)
                or not _bounded_int(profile.output_tokens, 1, profile.context_tokens)
                or not _bounded_int(profile.concurrency, 1, global_concurrency)
                or not _bounded_int(profile.timeout_ms, 1, 300_000)
                or not _bounded_int(profile.max_retries, 0, 2)
                or (profile.measured_p95_latency_ms is not None
                    and not _bounded_int(profile.measured_p95_latency_ms, 1, 300_000))):
                raise ValueError("invalid model limits")
            if not isinstance(profile.quality_by_task, Mapping):
                raise ValueError("invalid model quality metadata")
            ratings = dict(profile.quality_by_task)
            if any(task not in profile.tasks or not _bounded_int(score, 0, 100)
                   for task, score in ratings.items()):
                raise ValueError("invalid model quality metadata")
            # Copy mutable metadata: caller must not change model policy after registration.
            profile = replace(profile, quality_by_task=MappingProxyType(ratings))
            names.add(profile.name)
            self._models.append((profile, backend, asyncio.Semaphore(profile.concurrency)))

    async def generate(self, request: RouteRequest) -> Completion:
        if (type(request.task) is not str or not request.task
            or type(request.prompt) is not str or not request.prompt
            or (request.system_prompt is not None and type(request.system_prompt) is not str)
            or not _privacy(request.privacy)
            or not _bounded_int(request.min_quality, 0, 100)
            or not _bounded_int(request.max_input_tokens, 1, 10_000_000)
            or not _bounded_int(request.max_output_tokens, 1, 10_000_000)
            or not _bounded_int(request.max_total_tokens, 1, 10_000_000)
            or not _bounded_int(request.deadline_ms, 1, 300_000)
            or (request.max_p95_latency_ms is not None
                and not _bounded_int(request.max_p95_latency_ms, 1, 300_000))
            or not _bounded_int(request.max_external_cost_microusd, 0, 0)
            or (request.allowed_models is not None
                and (type(request.allowed_models) is not frozenset
                     or any(type(m) is not str for m in request.allowed_models)))):
            raise RouteDenied("invalid or forbidden request budget")
        if request.max_input_tokens + request.max_output_tokens < 2:
            raise RouteDenied("invalid token budgets")
        if self._inflight >= self._max_inflight_requests:
            raise RouteDenied("local inference admission capacity reached")
        # Single event loop: reserve BEFORE ANY await, release on all exit paths.
        self._inflight += 1
        deadline = time.monotonic() + request.deadline_ms / 1000
        try:
            eligible: list[tuple[ModelProfile, AsyncBackend, asyncio.Semaphore, int]] = []
            for profile, backend, semaphore in self._models:
                if (request.task not in profile.tasks or request.privacy > profile.max_privacy
                    or (request.allowed_models is not None and profile.name not in request.allowed_models)
                    or request.max_output_tokens > profile.output_tokens
                    or (request.min_quality > 0 and profile.quality_by_task.get(request.task, -1) < request.min_quality)
                    or (request.max_p95_latency_ms is not None and
                        (profile.measured_p95_latency_ms is None or
                         profile.measured_p95_latency_ms > request.max_p95_latency_ms))):
                    continue
                try:
                    n = backend.count_prompt_tokens(request.prompt, request.system_prompt)
                except Exception:
                    # Unavailable tokenizer = not eligible. Never guess word count.
                    continue
                if (type(n) is not int or n < 1 or n > request.max_input_tokens
                    or n + request.max_output_tokens > request.max_total_tokens
                    or n + request.max_output_tokens > profile.context_tokens):
                    continue
                eligible.append((profile, backend, semaphore, n))
            if not eligible:
                raise RouteDenied("no eligible local model or verified tokenizer")
            eligible.sort(key=lambda x: (
                -x[0].quality_by_task.get(request.task, 0),
                x[0].measured_p95_latency_ms if x[0].measured_p95_latency_ms is not None else float("inf"),
                x[0].name,
            ))
            for profile, backend, semaphore, prompt_tokens in eligible:
                for attempt in range(profile.max_retries + 1):
                    remaining = min(profile.timeout_ms / 1000, deadline - time.monotonic())
                    if remaining <= 0:
                        raise InferenceFailed("local inference deadline exceeded")

                    async def once() -> Completion:
                        async with self._global_semaphore:
                            async with semaphore:
                                return await backend.generate(request, max_output_tokens=request.max_output_tokens)

                    try:
                        result = await asyncio.wait_for(once(), timeout=remaining)
                    except asyncio.CancelledError:
                        raise  # No retry or fallback on cancellation.
                    except (asyncio.TimeoutError, TransientModelError):
                        if attempt == profile.max_retries:
                            break
                        continue
                    except PermanentModelError:
                        raise InferenceFailed("non-retryable local model failure") from None
                    except Exception:
                        raise InferenceFailed("unclassified local model failure") from None
                    if (not isinstance(result, Completion) or result.model != profile.name
                        or type(result.text) is not str
                        or type(result.prompt_tokens) is not int
                        or type(result.completion_tokens) is not int
                        or result.prompt_tokens != prompt_tokens
                        or not 0 <= result.completion_tokens <= request.max_output_tokens
                        or (result.ttft_ms is not None
                            and (type(result.ttft_ms) not in (float, int)
                                 or not math.isfinite(result.ttft_ms) or result.ttft_ms < 0))):
                        raise InferenceFailed("model identity or token usage mismatch")
                    return result
            raise InferenceFailed("all eligible local model attempts failed")
        finally:
            self._inflight -= 1
