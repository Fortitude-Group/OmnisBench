# SPDX-License-Identifier: Apache-2.0
"""Perturbation-gap contamination probe.

Score each model on the original problems and on reworded copies that keep the test cases
identical, then report the drop per model. A large gap means the score rode on the exact
wording. See docs/perturbation-probe.md.
"""
from __future__ import annotations

from .cache import ResponseCache
from .providers.base import ProviderRegistry
from .runner import ItemResult
from .types import CompletionRequest, ModelRef, TaskItem

_REWORD_SYSTEM = (
    "You reword competitive-programming problems for a paraphrase-robustness test. "
    "Rewrite the problem statement in different words: change the prose, the variable and "
    "quantity names, and the surface story. Keep the input format, the output format, every "
    "numeric constraint and limit, and the meaning identical, so the same inputs still produce "
    "the same correct outputs. Do not solve it, do not add or drop a constraint, and return "
    "only the reworded statement."
)


def _reword_request(prompt: str, max_tokens: int) -> CompletionRequest:
    return CompletionRequest(
        [{"role": "system", "content": _REWORD_SYSTEM}, {"role": "user", "content": prompt}],
        max_tokens,
    )


def tag_originals(items: list[TaskItem]) -> None:
    """Mark the untouched items as the original variant, in place."""
    for it in items:
        it.meta["variant"] = "original"


def generate_perturbations(
    items: list[TaskItem],
    generator: ModelRef,
    providers: ProviderRegistry,
    cache: ResponseCache,
    max_tokens: int = 2048,
) -> list[TaskItem]:
    """Reword each item's prompt with the generator model, keeping reference and tests.

    Generation is cached, so it reproduces, and the perturbed prompts are published in the
    run for anyone to inspect. The reference (test cases) is carried across unchanged, which
    is what keeps the grade comparable.
    """
    out: list[TaskItem] = []
    for it in items:
        resp = providers.complete_cached(_reword_request(it.prompt, max_tokens), generator, cache)
        reworded = resp.text.strip() or it.prompt
        out.append(TaskItem(
            id=f"{it.id}#pert",
            dataset=it.dataset,
            prompt=reworded,
            reference=it.reference,
            grader=it.grader,
            meta={**it.meta, "variant": "perturbed", "orig_id": it.id},
        ))
    return out


def _pass_map(results: list[ItemResult]) -> dict[tuple[str, str, str, str], bool]:
    passed: dict[tuple[str, str, str, str], bool] = {}
    for r in results:
        variant = r.meta.get("variant")
        if variant not in ("original", "perturbed"):
            continue
        base = str(r.meta.get("orig_id", r.item_id))
        passed[(r.chosen_model, variant, r.dataset, base)] = bool(r.passed)
    return passed


def _validated_tasks(passed: dict) -> set[tuple[str, str]]:
    """Tasks whose original and reworded copy are each solved by at least one model.

    Drops a rewording no model can solve (treated as broken, not as memorisation) and a
    problem no model solved at all (uninformative for a gap). This is the validation pass:
    it uses the whole pool rather than one model's judgement, so it isn't circular.
    """
    models = {m for (m, _v, _d, _b) in passed}
    tasks = {(d, b) for (_m, _v, d, b) in passed}
    kept = set()
    for d, b in tasks:
        orig_any = any(passed.get((m, "original", d, b), False) for m in models)
        pert_any = any(passed.get((m, "perturbed", d, b), False) for m in models)
        if orig_any and pert_any:
            kept.add((d, b))
    return kept


def perturbation_validation(results: list[ItemResult]) -> dict:
    """How many tasks the validation pass kept and dropped, with the dropped ids."""
    passed = _pass_map(results)
    tasks = {(d, b) for (_m, _v, d, b) in passed}
    kept = _validated_tasks(passed)
    return {"tasks": len(tasks), "kept": len(kept),
            "dropped": sorted(f"{d}/{b}" for (d, b) in (tasks - kept))}


def perturbation_gaps(results: list[ItemResult], validate: bool = False) -> dict[str, dict]:
    """Per-model accuracy on original vs reworded items, and the gap between them.

    Keyed by the model that answered. A pure function of the stored pass flags, so
    ``omnisbench verify`` re-derives it. With ``validate=True`` the gap is computed only
    over tasks that survive the validation pass. Models missing either variant are skipped.
    """
    passed = _pass_map(results)
    tasks = _validated_tasks(passed) if validate else {(d, b) for (_m, _v, d, b) in passed}
    models = sorted({m for (m, _v, _d, _b) in passed})

    out: dict[str, dict] = {}
    for m in models:
        keys = sorted(tasks)
        orig = [passed[(m, "original", d, b)] for d, b in keys if (m, "original", d, b) in passed]
        pert = [passed[(m, "perturbed", d, b)] for d, b in keys if (m, "perturbed", d, b) in passed]
        if not orig or not pert:
            continue
        acc_o = sum(orig) / len(orig)
        acc_p = sum(pert) / len(pert)
        out[m] = {"n": min(len(orig), len(pert)),
                  "acc_original": acc_o, "acc_perturbed": acc_p, "gap": acc_o - acc_p}
    return out
