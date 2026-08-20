# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from omnisbench.cache import ResponseCache
from omnisbench.cost import CostModel
from omnisbench.policies.baselines import AlwaysModelPolicy
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.runner import (
    ItemResult,
    aggregate,
    build_results_doc,
    contamination_counts,
    frontier_model_key,
    run_matrix,
    split_leaderboards,
)
from omnisbench.types import ModelRef, TaskItem, Usage

SNAP = Path("tests/fixtures/pricing/2026-08-18.yaml")

BIG = "anthropic/claude-big"
CHEAP = "openrouter/deepseek/deepseek-chat"


def _ir(policy, item_id, chosen, contamination="unknown", passed=True, cost=0.001):
    return ItemResult(
        policy=policy, dataset="mini", item_id=item_id, grader="exact_match",
        reference="x", meta={"contamination": contamination}, response_text="x",
        chosen_model=chosen, passed=passed, cost_usd=cost,
        input_tokens=10, output_tokens=10, latency_ms=1.0,
    )


def _setup(tmp_path):
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", lambda req, m: ("Paris", Usage(1000, 100))))
    items = [TaskItem("i1", "mini", "Capital of France?", "Paris", "exact_match", {})]
    policies = [AlwaysModelPolicy("always_big", ModelRef("anthropic", "claude-big"))]
    return reg, items, policies, ResponseCache(tmp_path), CostModel(SNAP)


def test_run_and_aggregate(tmp_path):
    reg, items, policies, cache, cost = _setup(tmp_path)
    results, unpriced = run_matrix(items, policies, reg, cache, cost)
    assert unpriced == []
    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].grader == "exact_match"
    assert results[0].reference == "Paris"
    assert results[0].response_text == "Paris"
    aggs = aggregate(results, {"always_big": "transparent"})
    assert aggs[0].quality == 1.0
    assert aggs[0].total_cost_usd > 0
    assert aggs[0].quality_per_usd > 0


def test_results_doc_shape(tmp_path):
    reg, items, policies, cache, cost = _setup(tmp_path)
    results, _unpriced = run_matrix(items, policies, reg, cache, cost)
    aggs = aggregate(results, {"always_big": "transparent"})
    doc = build_results_doc(aggs, results, {"snapshot_date": "2026-08-18"})
    assert doc["provenance"]["snapshot_date"] == "2026-08-18"
    assert doc["leaderboard"][0]["policy"] == "always_big"
    assert len(doc["items"]) == 1
    assert doc["items"][0]["response_text"] == "Paris"


def test_unpriced_model_costs_zero_and_is_reported(tmp_path):
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", lambda req, m: ("Paris", Usage(1000, 100))))
    items = [TaskItem("i1", "mini", "Capital of France?", "Paris", "exact_match", {})]
    policies = [AlwaysModelPolicy("always_unknown", ModelRef("anthropic", "does-not-exist"))]
    cache = ResponseCache(tmp_path)
    cost = CostModel(SNAP)

    results, unpriced = run_matrix(items, policies, reg, cache, cost)
    assert unpriced == ["anthropic/does-not-exist"]
    assert results[0].cost_usd == 0.0


def test_frontier_model_key_is_most_expensive_by_output_price():
    cost = CostModel(SNAP)
    results = [_ir("router", "a", CHEAP), _ir("router", "b", BIG)]
    # claude-big output is $75/Mtok vs deepseek $0.28, so it is the frontier.
    assert frontier_model_key(results, cost) == BIG


def test_frontier_ignores_unpriced_models():
    cost = CostModel(SNAP)
    results = [_ir("router", "a", "someprovider/unpriced"), _ir("router", "b", CHEAP)]
    assert frontier_model_key(results, cost) == CHEAP


def test_escape_rate_counts_frontier_routes():
    # router sends 1 of 2 to the frontier -> 0.5; always_cheap -> 0.0; always_big -> 1.0
    results = [
        _ir("router", "a", BIG), _ir("router", "b", CHEAP),
        _ir("always_cheap", "a", CHEAP), _ir("always_cheap", "b", CHEAP),
        _ir("always_big", "a", BIG), _ir("always_big", "b", BIG),
    ]
    aggs = {a.policy: a for a in aggregate(results, {}, frontier_key=BIG)}
    assert aggs["router"].escape_rate == 0.5
    assert aggs["always_cheap"].escape_rate == 0.0
    assert aggs["always_big"].escape_rate == 1.0


def test_escape_rate_is_zero_without_frontier():
    results = [_ir("router", "a", BIG)]
    assert aggregate(results, {})[0].escape_rate == 0.0


def test_split_leaderboards_group_by_contamination_fresh_first():
    results = [
        _ir("router", "c1", CHEAP, contamination="likely_contaminated"),
        _ir("router", "f1", BIG, contamination="fresh"),
    ]
    splits = split_leaderboards(results, {}, frontier_key=BIG)
    # fresh must sort ahead of likely_contaminated so the uncontaminated read leads
    assert list(splits.keys()) == ["fresh", "likely_contaminated"]
    assert splits["fresh"][0].n == 1
    assert splits["fresh"][0].escape_rate == 1.0
    assert splits["likely_contaminated"][0].escape_rate == 0.0


def test_contamination_counts_dedup_tasks_across_policies():
    results = [
        _ir("router", "t1", BIG, contamination="fresh"),
        _ir("always_big", "t1", BIG, contamination="fresh"),  # same task, other policy
        _ir("router", "t2", CHEAP, contamination="likely_contaminated"),
    ]
    assert contamination_counts(results) == {"fresh": 1, "likely_contaminated": 1}


def test_build_results_doc_carries_splits_and_frontier():
    results = [_ir("router", "f1", BIG, contamination="fresh")]
    aggs = aggregate(results, {}, frontier_key=BIG)
    splits = split_leaderboards(results, {}, frontier_key=BIG)
    doc = build_results_doc(
        aggs, results, {"snapshot_date": "2026-08-18"},
        frontier_model=BIG, splits=splits, contamination={"fresh": 1},
    )
    assert doc["frontier_model"] == BIG
    assert doc["contamination_counts"] == {"fresh": 1}
    assert "fresh" in doc["splits"]
    assert doc["leaderboard"][0]["escape_rate"] == 1.0
