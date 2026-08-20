# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ..cache import ResponseCache
from ..cost import CostModel
from ..graders import GRADERS  # importing registers every grader
from ..providers.base import ProviderRegistry
from ..types import ModelRef, TaskItem, Usage
from .base import MAX_TOKENS, PolicyOutcome, request_for


class OraclePolicy:
    kind = "transparent"

    def __init__(self, name: str, pool: list[ModelRef], cost: CostModel, max_tokens: int = MAX_TOKENS):
        self.name = name
        self._pool = pool
        self._cost = cost
        self._max_tokens = max_tokens

    def run(self, item: TaskItem, providers: ProviderRegistry, cache: ResponseCache) -> PolicyOutcome:
        grader = GRADERS[item.grader]
        req = request_for(item, self._max_tokens)
        scored: list[tuple[float, bool, ModelRef, str, Usage, float]] = []
        for model in self._pool:
            resp = providers.complete_cached(req, model, cache)
            passed = grader.score(resp.text, item).passed
            price = self._cost.price(model, resp.usage)
            scored.append((price, passed, model, resp.text, resp.usage, resp.latency_ms))
        passing = [s for s in scored if s[1]]
        chosen = min(passing, key=lambda s: s[0]) if passing else min(scored, key=lambda s: s[0])
        _, _, model, text, usage, latency = chosen
        return PolicyOutcome(text, model, usage, latency)
