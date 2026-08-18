# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from omnisbench.cache import ResponseCache
from omnisbench.cost import CostModel
from omnisbench.policies.baselines import AlwaysModelPolicy
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.runner import aggregate, build_results_doc, run_matrix
from omnisbench.types import ModelRef, TaskItem, Usage

SNAP = Path("tests/fixtures/pricing/2026-08-18.yaml")


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
