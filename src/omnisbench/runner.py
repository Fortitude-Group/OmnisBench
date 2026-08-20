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
    # Fraction of this policy's items routed to the frontier (most expensive) model.
    # 0.0 for always-cheap, 1.0 for always-frontier; for a real router it is the
    # escalation rate. Defaults to 0.0 when no frontier model is known.
    escape_rate: float = 0.0


UNKNOWN_SPLIT = "unknown"


def contamination_of(result: ItemResult) -> str:
    """The contamination split a result belongs to, from its task meta.

    Datasets are tagged in config (``contamination: likely_contaminated`` /
    ``fresh``); untagged tasks fall into ``unknown``.
    """
    return result.meta.get("contamination", UNKNOWN_SPLIT)


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


def aggregate(
    results: list[ItemResult],
    policy_kinds: dict[str, str],
    frontier_key: str | None = None,
) -> list[PolicyAggregate]:
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
        escape = (
            sum(1 for r in rs if r.chosen_model == frontier_key) / n
            if frontier_key is not None else 0.0
        )
        aggs.append(PolicyAggregate(policy, policy_kinds.get(policy, "transparent"),
                                    n, quality, total_cost, avg_cost, qpd, escape))
    return sorted(aggs, key=lambda a: a.quality_per_usd, reverse=True)


def frontier_model_key(results: list[ItemResult], cost: CostModel) -> str | None:
    """The most expensive model that appears in the results, by output price.

    This is the "frontier" a policy escalates to. Ties break on the model key so
    the choice is deterministic and re-derivable during verification.
    """
    best: str | None = None
    best_rate = float("-inf")
    for key in sorted({r.chosen_model for r in results}):
        rate = cost.output_rate(key)
        if rate is None:
            continue
        if rate > best_rate:
            best_rate, best = rate, key
    return best


def split_leaderboards(
    results: list[ItemResult],
    policy_kinds: dict[str, str],
    frontier_key: str | None = None,
) -> dict[str, list[PolicyAggregate]]:
    """A separate leaderboard per contamination split.

    Lets the honest question be answered directly: does the routing story hold on
    tasks the models cannot have memorised? Splits are sorted with ``fresh`` first,
    then the rest alphabetically, so the uncontaminated read leads.
    """
    by_split: dict[str, list[ItemResult]] = {}
    for r in results:
        by_split.setdefault(contamination_of(r), []).append(r)

    def order(name: str) -> tuple[int, str]:
        rank = {"fresh": 0, "likely_contaminated": 2, UNKNOWN_SPLIT: 3}.get(name, 1)
        return (rank, name)

    return {
        split: aggregate(rs, policy_kinds, frontier_key)
        for split, rs in sorted(by_split.items(), key=lambda kv: order(kv[0]))
    }


def contamination_counts(results: list[ItemResult]) -> dict[str, int]:
    """Distinct task count per contamination split (deduped across policies)."""
    seen: dict[str, set[tuple[str, str]]] = {}
    for r in results:
        seen.setdefault(contamination_of(r), set()).add((r.dataset, r.item_id))
    return {split: len(tasks) for split, tasks in sorted(seen.items())}


def build_results_doc(
    aggregates: list[PolicyAggregate],
    items: list[ItemResult],
    provenance: dict,
    *,
    frontier_model: str | None = None,
    splits: dict[str, list[PolicyAggregate]] | None = None,
    contamination: dict[str, int] | None = None,
) -> dict:
    doc: dict = {
        "provenance": provenance,
        "frontier_model": frontier_model,
        "contamination_counts": contamination or {},
        "leaderboard": [asdict(a) for a in aggregates],
        "splits": {
            split: [asdict(a) for a in aggs] for split, aggs in (splits or {}).items()
        },
        "items": [asdict(i) for i in items],
    }
    return doc
