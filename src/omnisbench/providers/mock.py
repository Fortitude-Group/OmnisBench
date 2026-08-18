# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Callable

from ..types import CompletionRequest, CompletionResponse, ModelRef, Usage


class MockProvider:
    def __init__(self, name: str, responder: Callable[[CompletionRequest, ModelRef], tuple[str, Usage]]):
        self.name = name
        self._responder = responder

    def complete(self, req: CompletionRequest, model: ModelRef) -> CompletionResponse:
        text, usage = self._responder(req, model)
        return CompletionResponse(text, model, usage, latency_ms=0.0, from_cache=False, raw={})
