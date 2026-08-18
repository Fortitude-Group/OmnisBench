# SPDX-License-Identifier: Apache-2.0
import json

import httpx

from omnisbench.providers.openai_compat import OpenAICompatProvider
from omnisbench.types import CompletionRequest, ModelRef, Usage


def _handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path.endswith("/chat/completions")
    return httpx.Response(200, json={
        "choices": [{"message": {"content": "42"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 1},
    })


def test_openai_compat_parses_response():
    provider = OpenAICompatProvider(
        "openai", "https://api.example/v1", "key",
        transport=httpx.MockTransport(_handler),
    )
    resp = provider.complete(
        CompletionRequest([{"role": "user", "content": "6*7?"}], 8),
        ModelRef("openai", "gpt-mid"),
    )
    assert resp.text == "42"
    assert resp.usage == Usage(11, 1)
    assert resp.from_cache is False
    assert resp.latency_ms >= 0


def _capturing_handler(captured: dict):
    def _handle(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "42"}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 1},
        })
    return _handle


def test_reasoning_model_body_uses_max_completion_tokens_and_omits_sampling():
    captured: dict = {}
    provider = OpenAICompatProvider(
        "openai", "https://api.example/v1", "key",
        transport=httpx.MockTransport(_capturing_handler(captured)),
        token_param="max_completion_tokens",
        send_sampling=False,
    )
    provider.complete(
        CompletionRequest([{"role": "user", "content": "6*7?"}], 8),
        ModelRef("openai", "gpt-5"),
    )
    body = captured["body"]
    assert body["max_completion_tokens"] == 8
    assert "max_tokens" not in body
    assert "temperature" not in body
    assert "seed" not in body


def test_default_body_keeps_max_tokens_and_sampling():
    captured: dict = {}
    provider = OpenAICompatProvider(
        "openai", "https://api.example/v1", "key",
        transport=httpx.MockTransport(_capturing_handler(captured)),
    )
    provider.complete(
        CompletionRequest([{"role": "user", "content": "6*7?"}], 8),
        ModelRef("openai", "gpt-mid"),
    )
    body = captured["body"]
    assert body["max_tokens"] == 8
    assert "temperature" in body
    assert "seed" in body
