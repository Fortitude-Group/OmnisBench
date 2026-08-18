# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import yaml

from .types import ModelRef, Usage


class CostModel:
    def __init__(self, snapshot_path: Path):
        data = yaml.safe_load(Path(snapshot_path).read_text(encoding="utf-8"))
        self.snapshot_date: str = data["snapshot_date"]
        self._models: dict[str, dict] = data["models"]

    def price(self, model: ModelRef, usage: Usage) -> float:
        rates = self._models[model.key]  # KeyError on unknown model — intentional, fail loud
        return (
            usage.input_tokens / 1_000_000 * rates["input_per_mtok"]
            + usage.output_tokens / 1_000_000 * rates["output_per_mtok"]
        )
