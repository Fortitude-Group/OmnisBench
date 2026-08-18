# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import asdict, dataclass

from .cache import ResponseCache
from .cost import CostModel
from .graders.code_unittest import GRADERS
from .policies.base import RoutingPolicy
from .providers.base import ProviderRegistry
from .types import TaskItem


@dataclass
class ItemResult:
    policy: str
    dataset: str
    item_id: str
    grader: str
    reference: object
    meta: dict
    response_text: str
    chosen_model: str
    passed: bool
    cost_usd: float
    input_tokens: int
    output_tokens: int
    latency_ms: float


@dataclass
class PolicyAggregate:
    policy: str
    kind: str
    n: int
    quality: float
    total_cost_usd: float
    avg_cost_usd: float
    quality_per_usd: float


def run_matrix(
    items: list[TaskItem],
    policies: list[RoutingPolicy],
    providers: ProviderRegistry,
    cache: ResponseCache,
    cost: CostModel,
) -> tuple[list[ItemResult], list[str]]:
    results: list[ItemResult] = []
    unpriced_models: set[str] = set()
    for policy in policies:
        for item in items:
            outcome = policy.run(item, providers, cache)
            passed = GRADERS[item.grader].score(outcome.response_text, item).passed
            try:
                price = cost.price(outcome.chosen_model, outcome.usage)
            except KeyError:
                price = 0.0
                unpriced_models.add(outcome.chosen_model.key)
            results.append(ItemResult(
                policy=policy.name,
                dataset=item.dataset,
                item_id=item.id,
                grader=item.grader,
                reference=item.reference,
                meta=item.meta,
                response_text=outcome.response_text,
                chosen_model=outcome.chosen_model.key,
                passed=passed,
                cost_usd=price,
                input_tokens=outcome.usage.input_tokens,
                output_tokens=outcome.usage.output_tokens,
                latency_ms=outcome.latency_ms,
            ))
    if unpriced_models:
        print(f"WARNING: no pricing snapshot entry for models: {sorted(unpriced_models)} — costed as $0.00")
    return results, sorted(unpriced_models)


def aggregate(results: list[ItemResult], policy_kinds: dict[str, str]) -> list[PolicyAggregate]:
    by_policy: dict[str, list[ItemResult]] = {}
    for r in results:
        by_policy.setdefault(r.policy, []).append(r)
    aggs: list[PolicyAggregate] = []
    for policy, rs in by_policy.items():
        n = len(rs)
        quality = sum(r.passed for r in rs) / n
        total_cost = sum(r.cost_usd for r in rs)
        avg_cost = total_cost / n
        qpd = quality / total_cost if total_cost > 0 else 0.0
        aggs.append(PolicyAggregate(policy, policy_kinds.get(policy, "transparent"),
                                    n, quality, total_cost, avg_cost, qpd))
    return sorted(aggs, key=lambda a: a.quality_per_usd, reverse=True)


def build_results_doc(aggregates: list[PolicyAggregate], items: list[ItemResult], provenance: dict) -> dict:
    return {
        "provenance": provenance,
        "leaderboard": [asdict(a) for a in aggregates],
        "items": [asdict(i) for i in items],
    }
