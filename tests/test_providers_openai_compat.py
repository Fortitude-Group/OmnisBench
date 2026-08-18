# SPDX-License-Identifier: Apache-2.0
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
