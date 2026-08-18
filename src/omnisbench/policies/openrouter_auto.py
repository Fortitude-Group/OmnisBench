# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ..cache import ResponseCache
from ..providers.base import ProviderRegistry
from ..types import ModelRef, TaskItem
from .base import PolicyOutcome, request_for


class OpenRouterAutoPolicy:
    kind = "opaque"

    def __init__(self, name: str, meta_model: str = "openrouter/auto"):
        self.name = name
        self._meta = ModelRef("openrouter", meta_model)

    def run(self, item: TaskItem, providers: ProviderRegistry, cache: ResponseCache) -> PolicyOutcome:
        resp = providers.complete_cached(request_for(item), self._meta, cache)
        reported = resp.raw.get("model", self._meta.model_id)
        chosen = ModelRef("openrouter", reported)
        return PolicyOutcome(resp.text, chosen, resp.usage, resp.latency_ms)
