# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import yaml

from .cost import CostModel
from .policies.base import MAX_TOKENS
from .policies.baselines import AlwaysModelPolicy, RandomPolicy
from .policies.openrouter_auto import OpenRouterAutoPolicy
from .policies.oracle import OraclePolicy
from .types import ModelRef


def load_config(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _models(cfg: dict) -> dict[str, ModelRef]:
    return {name: ModelRef(m["provider"], m["model_id"]) for name, m in cfg["models"].items()}


def build_policies(cfg: dict, cost: CostModel):
    models = _models(cfg)
    max_tokens = int(cfg.get("max_tokens", MAX_TOKENS))
    policies = []
    kinds: dict[str, str] = {}
    for p in cfg["policies"]:
        t = p["type"]
        if t == "always_model":
            pol = AlwaysModelPolicy(p["name"], models[p["model"]], max_tokens)
        elif t == "random":
            pol = RandomPolicy(p["name"], [models[m] for m in p["pool"]], p.get("seed", 0), max_tokens)
        elif t == "oracle":
            pol = OraclePolicy(p["name"], [models[m] for m in p["pool"]], cost, max_tokens)
        elif t == "openrouter_auto":
            pol = OpenRouterAutoPolicy(p["name"], p.get("meta_model", "openrouter/auto"))
        else:
            raise ValueError(f"unknown policy type: {t}")
        policies.append(pol)
        kinds[pol.name] = pol.kind
    return policies, kinds
