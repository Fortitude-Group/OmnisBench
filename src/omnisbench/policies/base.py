# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..cache import ResponseCache
from ..providers.base import ProviderRegistry
from ..types import CompletionRequest, ModelRef, TaskItem, Usage

MAX_TOKENS = 1024


@dataclass
class PolicyOutcome:
    response_text: str
    chosen_model: ModelRef
    usage: Usage
    latency_ms: float


class RoutingPolicy(Protocol):
    name: str
    kind: str

    def run(self, item: TaskItem, providers: ProviderRegistry, cache: ResponseCache) -> PolicyOutcome: ...


def request_for(item: TaskItem) -> CompletionRequest:
    return CompletionRequest([{"role": "user", "content": item.prompt}], MAX_TOKENS)
