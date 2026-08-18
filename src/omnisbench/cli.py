# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .cache import ResponseCache
from .config import build_policies, load_config
from .cost import CostModel
from .datasets.loaders import load_dataset_spec
from .graders.code_unittest import GRADERS
from .providers.base import ProviderRegistry
from .providers.openai_compat import OpenAICompatProvider
from .report.html import render_report
from .runner import ItemResult, aggregate, build_results_doc, run_matrix
from .types import ModelRef, TaskItem, Usage


def build_providers(cfg: dict, env: dict) -> ProviderRegistry:
    reg = ProviderRegistry()
    for name, pc in cfg.get("providers", {}).items():
        reg.register(OpenAICompatProvider(name, pc["base_url"], env.get(pc["api_key_env"], "")))
    return reg


def _load_items(cfg: dict) -> list[TaskItem]:
    items: list[TaskItem] = []
    for spec in cfg["datasets"]:
        items.extend(load_dataset_spec(spec))
    return items


def cmd_run(cfg_path: str, run_dir: str, providers_override: ProviderRegistry | None = None) -> int:
    cfg = load_config(cfg_path)
    cost = CostModel(cfg["pricing"])
    providers = providers_override or build_providers(cfg, dict(os.environ))
    policies, kinds = build_policies(cfg, cost)
    items = _load_items(cfg)

    out = Path(run_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = ResponseCache(out / "cache")
    results, unpriced_models = run_matrix(items, policies, providers, cache, cost)
    aggs = aggregate(results, kinds)
    provenance = {
        "snapshot_date": cost.snapshot_date,
        "run_date": cfg.get("run_date", ""),
        "unpriced_models": unpriced_models,
    }
    doc = build_results_doc(aggs, results, provenance)
    (out / "results.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    shutil.copy(cfg["pricing"], out / Path(cfg["pricing"]).name)
    print(f"Wrote {out / 'results.json'} — {len(results)} item-results, {len(aggs)} policies")
    return 0


def cmd_report(run_dir: str) -> int:
    out = Path(run_dir)
    doc = json.loads((out / "results.json").read_text(encoding="utf-8"))
    (out / "report.html").write_text(render_report(doc), encoding="utf-8")
    print(f"Wrote {out / 'report.html'}")
    return 0


def cmd_verify(run_dir: str) -> int:
    """Re-run the graders and re-price from the data inlined in results.json.

    Genuine offline re-grading: no API/network calls. Re-derives both quality
    (by re-running each item's grader against its published response_text) and
    cost (by re-pricing chosen_model/usage against the pricing snapshot copied
    into the run directory), then re-aggregates the leaderboard and diffs it
    against the stored one.
    """
    out = Path(run_dir)
    doc = json.loads((out / "results.json").read_text(encoding="utf-8"))
    cost = CostModel(out / f"{doc['provenance']['snapshot_date']}.yaml")

    recomputed_items: list[ItemResult] = []
    unpriced_models: set[str] = set()
    ok = True
    for it in doc["items"]:
        task = TaskItem(
            it["item_id"], it["dataset"], "", it["reference"], it["grader"], it["meta"],
        )
        passed = GRADERS[it["grader"]].score(it["response_text"], task).passed
        provider, model_id = it["chosen_model"].split("/", 1)
        model = ModelRef(provider, model_id)
        usage = Usage(it["input_tokens"], it["output_tokens"])
        try:
            price = cost.price(model, usage)
        except KeyError:
            price = 0.0
            unpriced_models.add(model.key)

        if passed != bool(it["passed"]):
            print(
                f"MISMATCH {it['policy']}/{it['item_id']}: stored passed={it['passed']} "
                f"!= recomputed passed={passed}"
            )
            ok = False

        recomputed_items.append(ItemResult(
            policy=it["policy"],
            dataset=it["dataset"],
            item_id=it["item_id"],
            grader=it["grader"],
            reference=it["reference"],
            meta=it["meta"],
            response_text=it["response_text"],
            chosen_model=it["chosen_model"],
            passed=passed,
            cost_usd=price,
            input_tokens=it["input_tokens"],
            output_tokens=it["output_tokens"],
            latency_ms=it["latency_ms"],
        ))

    kinds = {row["policy"]: row["kind"] for row in doc["leaderboard"]}
    recomputed_aggs = {a.policy: a for a in aggregate(recomputed_items, kinds)}

    for row in doc["leaderboard"]:
        got = recomputed_aggs[row["policy"]]
        for field in ("quality", "total_cost_usd", "avg_cost_usd", "quality_per_usd"):
            stored_val = row[field]
            got_val = getattr(got, field)
            if abs(got_val - stored_val) > 1e-9:
                print(f"MISMATCH {row['policy']}.{field}: stored {stored_val} != recomputed {got_val}")
                ok = False

    if unpriced_models:
        print(f"WARNING: unpriced models in verify: {sorted(unpriced_models)} — costed as $0.00")

    print("VERIFY OK" if ok else "VERIFY FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="omnisbench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--config", required=True)
    r.add_argument("--run", required=True)
    rep = sub.add_parser("report")
    rep.add_argument("--run", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args.config, args.run)
    if args.cmd == "report":
        return cmd_report(args.run)
    if args.cmd == "verify":
        return cmd_verify(args.run)
    return 2


if __name__ == "__main__":
    sys.exit(main())
