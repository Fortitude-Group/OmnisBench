# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Protocol

from ..cache import ResponseCache, cache_key
from ..types import CompletionRequest, CompletionResponse, ModelRef


class Provider(Protocol):
    name: str

    def complete(self, req: CompletionRequest, model: ModelRef) -> CompletionResponse: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        self._providers[provider.name] = provider

    def get(self, provider_name: str) -> Provider:
        return self._providers[provider_name]

    def complete_cached(
        self, req: CompletionRequest, model: ModelRef, cache: ResponseCache
    ) -> CompletionResponse:
        key = cache_key(req.cache_payload(model))
        hit = cache.get(key)
        if hit is not None:
            return hit
        resp = self.get(model.provider).complete(req, model)
        cache.put(key, resp)
        return resp
