# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from omnisbench.cache import ResponseCache
from omnisbench.cost import CostModel
from omnisbench.policies.oracle import OraclePolicy
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.types import ModelRef, TaskItem, Usage

SNAP = Path("tests/fixtures/pricing/2026-08-18.yaml")


def _reg():
    # cheap model answers wrong; big model answers right
    def responder(req, m):
        if m.model_id == "claude-big":
            return ("Paris", Usage(10, 1))
        return ("London", Usage(10, 1))
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", responder))
    reg.register(MockProvider("openrouter", responder))
    return reg


def _item():
    return TaskItem("t", "ds", "Capital of France? one word.", "Paris", "exact_match", {})


def test_oracle_picks_cheapest_passing_model(tmp_path):
    pool = [ModelRef("openrouter", "deepseek/deepseek-chat"), ModelRef("anthropic", "claude-big")]
    p = OraclePolicy("oracle", pool, CostModel(SNAP))
    out = p.run(_item(), _reg(), ResponseCache(tmp_path))
    # cheap model got it wrong, so oracle must escalate to the big (correct) model
    assert out.chosen_model == ModelRef("anthropic", "claude-big")
    assert out.response_text == "Paris"
