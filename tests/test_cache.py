# SPDX-License-Identifier: Apache-2.0
from omnisbench.cache import ResponseCache, cache_key
from omnisbench.types import CompletionResponse, ModelRef, Usage


def test_cache_key_is_order_independent():
    assert cache_key({"a": 1, "b": 2}) == cache_key({"b": 2, "a": 1})


def test_put_then_get_roundtrips(tmp_path):
    cache = ResponseCache(tmp_path)
    resp = CompletionResponse("hello", ModelRef("openai", "m"), Usage(3, 5), 12.0, False, {"x": 1})
    cache.put("abc123", resp)
    got = cache.get("abc123")
    assert got is not None
    assert got.text == "hello"
    assert got.usage == Usage(3, 5)
    assert got.model == ModelRef("openai", "m")
    assert got.from_cache is True  # reads are always flagged as cache hits


def test_get_miss_returns_none(tmp_path):
    assert ResponseCache(tmp_path).get("missing") is None
