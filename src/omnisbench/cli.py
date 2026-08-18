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
from .providers.base import ProviderRegistry
from .providers.openai_compat import OpenAICompatProvider
from .report.html import render_report
from .runner import aggregate, build_results_doc, run_matrix
from .types import TaskItem


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
    results = run_matrix(items, policies, providers, cache, cost)
    aggs = aggregate(results, kinds)
    provenance = {"snapshot_date": cost.snapshot_date, "run_date": cfg.get("run_date", "")}
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
    """Re-derive leaderboard quality from stored per-item pass/fail. No API calls."""
    out = Path(run_dir)
    doc = json.loads((out / "results.json").read_text(encoding="utf-8"))
    recomputed: dict[str, list[bool]] = {}
    for it in doc["items"]:
        recomputed.setdefault(it["policy"], []).append(bool(it["passed"]))
    ok = True
    for row in doc["leaderboard"]:
        got = sum(recomputed[row["policy"]]) / len(recomputed[row["policy"]])
        if abs(got - row["quality"]) > 1e-9:
            print(f"MISMATCH {row['policy']}: stored {row['quality']} != recomputed {got}")
            ok = False
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
