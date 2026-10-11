"""Offline-first, provider-neutral *policy* router; no live inference integration.

This module creates no network connections, processes or model downloads. A
caller must inject a model-specific tokenizer and an async backend. Never
register a cloud backend without a separately reviewed authorization design.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Mapping, Protocol


class Privacy(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class RouteDenied(Exception):
    """No model passes every constraint; no inference was initiated."""


class TransientModelError(Exception):
    """Retryable local-model failure (unavailable/overloaded)."""


class PermanentModelError(Exception):
    """Non-retryable failure (e.g. safety policy or invalid request)."""


class InferenceFailed(Exception):
    """All eligible backends failed without exposing prompts or provider logs."""


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
        """Use the model's exact tokenizer INCLUDING chat template/system tokens."""
        ...

    async def generate(self, request: RouteRequest, *, max_output_tokens: int) -> Completion:
        """Must respect cancellation and enforce output cap server-side."""
        ...


class ModelRouter:
    def __init__(self, registrations: list[tuple[ModelProfile, AsyncBackend]], *, global_concurrency: int = 1):
        if global_concurrency < 1 or global_concurrency > 32:
            raise ValueError("invalid global concurrency")
        self._global_semaphore = asyncio.Semaphore(global_concurrency)
        self._models: list[tuple[ModelProfile, AsyncBackend, asyncio.Semaphore]] = []
        names: set[str] = set()
        for profile, backend in registrations:
            if not profile.name or profile.name in names:
                raise ValueError("duplicate/empty model name")
            if profile.deployment != "local" or profile.external_cost_microusd != 0:
                raise ValueError("only zero-external-cost local backends allowed")
            if (not profile.tasks or profile.context_tokens < 1 or profile.output_tokens < 1
                or profile.concurrency < 1 or profile.timeout_ms < 1
                or not 0 <= profile.max_retries <= 2):
                raise ValueError("invalid model limits")
            names.add(profile.name)
            self._models.append((profile, backend, asyncio.Semaphore(profile.concurrency)))

    async def generate(self, request: RouteRequest) -> Completion:
        if (not request.task or not request.prompt or request.max_input_tokens < 1
            or request.max_output_tokens < 1 or request.max_total_tokens < 1
            or request.deadline_ms < 1 or request.min_quality < 0
            or request.max_external_cost_microusd < 0
            or (request.max_p95_latency_ms is not None and request.max_p95_latency_ms < 1)):
            raise RouteDenied("invalid request budget")
        if request.max_external_cost_microusd != 0:
            raise RouteDenied("external spending is disabled")
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
                # Unknown tokenizer => fail closed for this profile.
                continue
            if (type(n) is not int or n < 1 or n > request.max_input_tokens
                or n + request.max_output_tokens > request.max_total_tokens
                or n + request.max_output_tokens > profile.context_tokens):
                continue
            eligible.append((profile, backend, semaphore, n))
        if not eligible:
            raise RouteDenied("no eligible local model or verified tokenizer")
        eligible.sort(key=lambda x: (-x[0].quality_by_task.get(request.task, 0),
                                     x[0].measured_p95_latency_ms if x[0].measured_p95_latency_ms is not None else float("inf"),
                                     x[0].name))
        deadline = time.monotonic() + request.deadline_ms / 1000
        # Attempt only eligible local backends, no implicit quality/privacy downgrade.
        for profile, backend, semaphore, prompt_tokens in eligible:
            for attempt in range(profile.max_retries + 1):
                remaining = min(profile.timeout_ms / 1000, deadline - time.monotonic())
                if remaining <= 0:
                    raise InferenceFailed("model request deadline exceeded")
                async def once() -> Completion:
                    async with self._global_semaphore:
                        async with semaphore:
                            return await backend.generate(request, max_output_tokens=request.max_output_tokens)
                try:
                    result = await asyncio.wait_for(once(), timeout=remaining)
                except asyncio.CancelledError:
                    raise  # No retry or fallback after caller cancellation.
                except (asyncio.TimeoutError, TransientModelError):
                    if attempt == profile.max_retries:
                        break
                    continue  # bounded retries, no exponential unbounded loop
                except PermanentModelError:
                    raise InferenceFailed("non-retryable local model failure") from None
                except Exception:
                    # Unknown faults are not retryable, never copy exception text.
                    raise InferenceFailed("unclassified local model failure") from None
                if (result.model != profile.name or type(result.prompt_tokens) is not int
                    or type(result.completion_tokens) is not int
                    or result.prompt_tokens != prompt_tokens
                    or not 0 <= result.completion_tokens <= request.max_output_tokens):
                    # Budget violation is an incident; do not silently fallback.
                    raise InferenceFailed("model identity or token usage mismatch")
                return result
        raise InferenceFailed("all eligible local model attempts failed")
