# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import random

from ..cache import ResponseCache
from ..providers.base import ProviderRegistry
from ..types import ModelRef, TaskItem
from .base import PolicyOutcome, request_for


class AlwaysModelPolicy:
    kind = "transparent"

    def __init__(self, name: str, model: ModelRef):
        self.name = name
        self._model = model

    def run(self, item: TaskItem, providers: ProviderRegistry, cache: ResponseCache) -> PolicyOutcome:
        resp = providers.complete_cached(request_for(item), self._model, cache)
        return PolicyOutcome(resp.text, self._model, resp.usage, resp.latency_ms)


class RandomPolicy:
    kind = "transparent"

    def __init__(self, name: str, pool: list[ModelRef], seed: int):
        self.name = name
        self._pool = pool
        self._seed = seed

    def _pick(self, item: TaskItem) -> ModelRef:
        rng = random.Random(f"{self._seed}:{item.id}")
        return self._pool[rng.randrange(len(self._pool))]

    def run(self, item: TaskItem, providers: ProviderRegistry, cache: ResponseCache) -> PolicyOutcome:
        model = self._pick(item)
        resp = providers.complete_cached(request_for(item), model, cache)
        return PolicyOutcome(resp.text, model, resp.usage, resp.latency_ms)
