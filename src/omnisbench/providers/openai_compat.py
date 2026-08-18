# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import time

import httpx

from ..types import CompletionRequest, CompletionResponse, ModelRef, Usage


class OpenAICompatProvider:
    def __init__(self, name: str, base_url: str, api_key: str, transport: httpx.BaseTransport | None = None):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
            transport=transport,
        )

    def complete(self, req: CompletionRequest, model: ModelRef) -> CompletionResponse:
        body = {
            "model": model.model_id,
            "messages": req.messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "seed": req.seed,
        }
        if req.stop:
            body["stop"] = list(req.stop)
        start = time.perf_counter()
        r = self._client.post("/chat/completions", json=body)
        latency_ms = (time.perf_counter() - start) * 1000
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        return CompletionResponse(
            text=text,
            model=model,
            usage=Usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)),
            latency_ms=latency_ms,
            from_cache=False,
            raw=data,
        )
