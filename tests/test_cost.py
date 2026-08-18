# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from omnisbench.cost import CostModel
from omnisbench.types import ModelRef, Usage

SNAP = Path("tests/fixtures/pricing/2026-08-18.yaml")


def test_price_computes_from_snapshot():
    cost = CostModel(SNAP)
    # 1,000,000 input + 1,000,000 output of claude-big = 15 + 75 = 90 USD
    price = cost.price(ModelRef("anthropic", "claude-big"), Usage(1_000_000, 1_000_000))
    assert price == pytest.approx(90.0)


def test_unknown_model_raises():
    cost = CostModel(SNAP)
    with pytest.raises(KeyError):
        cost.price(ModelRef("openai", "does-not-exist"), Usage(1, 1))


def test_snapshot_date_exposed():
    assert CostModel(SNAP).snapshot_date == "2026-08-18"
