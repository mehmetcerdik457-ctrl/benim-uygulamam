from __future__ import annotations

from collections.abc import Mapping

from .protocol import ModelRequest, ModelResponse


class DeterministicFakeModelAdapter:
    """In-memory fake for offline tests; it performs no model inference."""

    def __init__(
        self,
        responses: Mapping[str, str] | None = None,
        *,
        default_response: str = "synthetic response",
    ) -> None:
        self._responses = dict(responses or {})
        self._default_response = default_response

    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            text=self._responses.get(request.prompt, self._default_response),
            model="synthetic-fake",
        )
