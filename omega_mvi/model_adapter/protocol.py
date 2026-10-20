from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    system_prompt: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str


class ModelAdapter(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse:
        ...
