# SPDX-License-Identifier: Apache-2.0
from omnisbench.cache import ResponseCache
from omnisbench.policies.baselines import AlwaysModelPolicy, RandomPolicy
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.types import ModelRef, TaskItem, Usage


def _reg():
    reg = ProviderRegistry()
    reg.register(MockProvider("mock", lambda req, m: (f"out:{m.model_id}", Usage(5, 1))))
    return reg


def _item():
    return TaskItem("t1", "ds", "prompt?", "x", "exact_match", {})


def test_always_model_routes_to_fixed_model(tmp_path):
    p = AlwaysModelPolicy("always_big", ModelRef("mock", "big"))
    out = p.run(_item(), _reg(), ResponseCache(tmp_path))
    assert out.chosen_model == ModelRef("mock", "big")
    assert out.response_text == "out:big"
    assert p.kind == "transparent"


def test_random_is_deterministic(tmp_path):
    pool = [ModelRef("mock", "a"), ModelRef("mock", "b")]
    p1 = RandomPolicy("random", pool, seed=3)
    p2 = RandomPolicy("random", pool, seed=3)
    reg, cache = _reg(), ResponseCache(tmp_path)
    assert p1.run(_item(), reg, cache).chosen_model == p2.run(_item(), reg, cache).chosen_model
