# SPDX-License-Identifier: Apache-2.0
from omnisbench.cache import ResponseCache
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.types import CompletionRequest, ModelRef, Usage


def _reg():
    reg = ProviderRegistry()
    reg.register(MockProvider("mock", lambda req, m: (f"ans:{m.model_id}", Usage(10, 2))))
    return reg


def test_complete_returns_response():
    reg = _reg()
    resp = reg.get("mock").complete(CompletionRequest([{"role": "user", "content": "q"}], 8),
                                    ModelRef("mock", "m1"))
    assert resp.text == "ans:m1"
    assert resp.usage == Usage(10, 2)
    assert resp.from_cache is False


def test_complete_cached_uses_cache_on_second_call(tmp_path):
    reg = _reg()
    cache = ResponseCache(tmp_path)
    req = CompletionRequest([{"role": "user", "content": "q"}], 8)
    model = ModelRef("mock", "m1")
    first = reg.complete_cached(req, model, cache)
    second = reg.complete_cached(req, model, cache)
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.text == first.text
