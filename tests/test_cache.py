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


def _priced(tmp_path):
    from omnisbench.cost import CostModel
    snap = tmp_path / "p.yaml"
    snap.write_text('snapshot_date: "x"\nmodels:\n  "openai/m": {input_per_mtok: 1.0, output_per_mtok: 10.0}\n',
                    encoding="utf-8")
    return CostModel(snap)


def _resp(out_tokens):
    return CompletionResponse("t", ModelRef("openai", "m"), Usage(0, out_tokens), 1.0, False, {})


def test_budgeted_cache_counts_spend_and_stops_over_the_cap(tmp_path):
    import pytest
    from omnisbench.cache import BudgetedCache, BudgetExceeded
    cache = BudgetedCache(tmp_path / "cache", _priced(tmp_path), max_usd=1.0)
    cache.put("a", _resp(60_000))          # $0.60
    assert cache.spent_usd == pytest.approx(0.60)
    with pytest.raises(BudgetExceeded):
        cache.put("b", _resp(60_000))      # $1.20, over the cap
    assert cache.get("b") is not None      # the paid-for answer is kept


def test_budgeted_cache_resumes_with_spend_so_far(tmp_path):
    import pytest
    from omnisbench.cache import BudgetedCache, BudgetExceeded
    BudgetedCache(tmp_path / "cache", _priced(tmp_path), max_usd=1.0).put("a", _resp(60_000))
    again = BudgetedCache(tmp_path / "cache", _priced(tmp_path), max_usd=1.0)
    assert again.spent_usd == pytest.approx(0.60)
    again.put("c", _resp(30_000))          # $0.90 total, still under
    with pytest.raises(BudgetExceeded):
        BudgetedCache(tmp_path / "cache", _priced(tmp_path), max_usd=0.90)
