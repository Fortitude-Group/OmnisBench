# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import random
from pathlib import Path

from ..types import TaskItem


def _shuffle_limit(items: list[TaskItem], limit: int | None, seed: int) -> list[TaskItem]:
    ordered = sorted(items, key=lambda i: i.id)
    random.Random(seed).shuffle(ordered)
    return ordered[:limit] if limit is not None else ordered


def load_jsonl(path: Path, dataset_name: str, limit: int | None, seed: int,
                prompt_prefix: str = "") -> list[TaskItem]:
    items: list[TaskItem] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        items.append(TaskItem(d["id"], dataset_name, f"{prompt_prefix}{d['prompt']}", d["reference"],
                              d["grader"], d.get("meta", {})))
    return _shuffle_limit(items, limit, seed)


def load_hf(spec: dict) -> list[TaskItem]:
    from datasets import load_dataset

    prompt_prefix = spec.get("prompt_prefix", "")
    ds = load_dataset(spec["name"], revision=spec.get("revision"), split=spec["split"])
    m = spec["mapping"]  # {"id","prompt","reference","grader","meta"?}
    items: list[TaskItem] = []
    for idx, row in enumerate(ds):
        items.append(TaskItem(
            id=str(row.get(m.get("id"), idx)),
            dataset=spec["name"],
            prompt=f"{prompt_prefix}{row[m['prompt']]}",
            reference=row[m["reference"]],
            grader=spec["grader"],
            meta={k: row[v] for k, v in m.get("meta", {}).items()},
        ))
    return _shuffle_limit(items, spec.get("limit"), spec.get("seed", 0))


def apply_min_date(items: list[TaskItem], min_date: str, date_key: str = "date") -> list[TaskItem]:
    """Keep only tasks dated on/after ``min_date`` (ISO ``YYYY-MM-DD`` string compare).

    This is how a "fresh", contamination-resistant split is built: filter a dated
    dataset (e.g. LiveCodeBench, whose problems carry a release date) down to
    problems published after the model pool's training cutoff. A task with no date
    under ``meta[date_key]`` is dropped, because an undated task cannot be shown to
    be fresh.
    """
    kept: list[TaskItem] = []
    for it in items:
        d = it.meta.get(date_key)
        if isinstance(d, str) and d >= min_date:
            kept.append(it)
    return kept


def stamp_contamination(items: list[TaskItem], value: str) -> None:
    """Tag every task with its contamination split, in place."""
    for it in items:
        it.meta["contamination"] = value


def load_dataset_spec(spec: dict) -> list[TaskItem]:
    kind = spec["kind"]
    if kind == "jsonl":
        items = load_jsonl(Path(spec["path"]), spec["name"], spec.get("limit"), spec.get("seed", 0),
                           spec.get("prompt_prefix", ""))
    elif kind == "hf":
        items = load_hf(spec)
    elif kind == "livecodebench":
        from .livecodebench import load_livecodebench
        items = load_livecodebench(spec)
    else:
        raise ValueError(f"unknown dataset kind: {kind}")

    min_date = spec.get("min_date")
    if min_date:
        items = apply_min_date(items, min_date, spec.get("date_key", "date"))
    stamp_contamination(items, spec.get("contamination", "unknown"))
    return items
