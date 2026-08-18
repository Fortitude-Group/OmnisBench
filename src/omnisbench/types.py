# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelRef:
    provider: str
    model_id: str

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.model_id}"


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class CompletionRequest:
    messages: list[dict]
    max_tokens: int
    temperature: float = 0.0
    seed: int = 0
    stop: tuple[str, ...] = ()

    def cache_payload(self, model: ModelRef) -> dict:
        return {
            "provider": model.provider,
            "model_id": model.model_id,
            "messages": self.messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "stop": list(self.stop),
        }


@dataclass
class CompletionResponse:
    text: str
    model: ModelRef
    usage: Usage
    latency_ms: float
    from_cache: bool
    raw: dict = field(default_factory=dict)


@dataclass
class TaskItem:
    id: str
    dataset: str
    prompt: str
    reference: Any
    grader: str
    meta: dict = field(default_factory=dict)


@dataclass
class GradeResult:
    passed: bool
    score: float
    detail: dict = field(default_factory=dict)
