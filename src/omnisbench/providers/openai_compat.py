# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import time

import httpx

from ..types import CompletionRequest, CompletionResponse, ModelRef, Usage


class OpenAICompatProvider:
    # Transient upstream statuses worth retrying rather than aborting a long run.
    # 529 is Anthropic "Overloaded"; 408 is request timeout.
    _RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504, 529})

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        token_param: str = "max_tokens",
        send_sampling: bool = True,
        timeout: float = 600.0,
        max_retries: int = 8,
    ):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._token_param = token_param
        self._send_sampling = send_sampling
        self._max_retries = max(1, max_retries)
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def complete(self, req: CompletionRequest, model: ModelRef) -> CompletionResponse:
        body: dict = {
            "model": model.model_id,
            "messages": req.messages,
            self._token_param: req.max_tokens,
        }
        if self._send_sampling:
            body["temperature"] = req.temperature
            body["seed"] = req.seed
        if req.stop:
            body["stop"] = list(req.stop)

        # A single slow reasoning generation (large max_tokens) or a transient 5xx/429
        # should not abort a long, paid run. Retry with linear backoff, then give up.
        for attempt in range(self._max_retries):
            try:
                start = time.perf_counter()
                r = self._client.post("/chat/completions", json=body)
                latency_ms = (time.perf_counter() - start) * 1000
                if r.status_code in self._RETRY_STATUS and attempt < self._max_retries - 1:
                    time.sleep(min(30.0, 5.0 * (attempt + 1)))
                    continue
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
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt < self._max_retries - 1:
                    time.sleep(min(30.0, 5.0 * (attempt + 1)))
                    continue
                raise
        # Exhausted retries on a retryable status: surface the last response's error.
        r.raise_for_status()
        raise RuntimeError("unreachable")  # pragma: no cover
