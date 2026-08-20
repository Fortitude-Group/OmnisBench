# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from omnisbench.datasets.loaders import (
    apply_min_date,
    load_dataset_spec,
    load_jsonl,
    stamp_contamination,
)
from omnisbench.types import TaskItem

FIX = Path("tests/fixtures/mini_dataset.jsonl")


def test_load_jsonl_maps_taskitems():
    items = load_jsonl(FIX, "mini", limit=None, seed=0)
    assert len(items) == 2
    assert {i.id for i in items} == {"m1", "m2"}
    assert all(i.dataset == "mini" for i in items)


def test_limit_is_deterministic():
    a = load_jsonl(FIX, "mini", limit=1, seed=7)
    b = load_jsonl(FIX, "mini", limit=1, seed=7)
    assert [i.id for i in a] == [i.id for i in b]


def test_dispatch_jsonl():
    items = load_dataset_spec({"kind": "jsonl", "path": str(FIX), "name": "mini", "seed": 0})
    assert len(items) == 2


def test_prompt_prefix_is_prepended_deterministically():
    prefix = "Answer briefly.\n\n"
    with_prefix = load_jsonl(FIX, "mini", limit=None, seed=0, prompt_prefix=prefix)
    without_prefix = load_jsonl(FIX, "mini", limit=None, seed=0)
    by_id = {i.id: i for i in without_prefix}
    for item in with_prefix:
        assert item.prompt == f"{prefix}{by_id[item.id].prompt}"


def test_dispatch_jsonl_applies_prompt_prefix():
    prefix = "PREFIX: "
    items = load_dataset_spec({
        "kind": "jsonl", "path": str(FIX), "name": "mini", "seed": 0, "prompt_prefix": prefix,
    })
    assert all(i.prompt.startswith(prefix) for i in items)


def test_contamination_defaults_to_unknown():
    items = load_dataset_spec({"kind": "jsonl", "path": str(FIX), "name": "mini", "seed": 0})
    assert all(i.meta["contamination"] == "unknown" for i in items)


def test_contamination_tag_is_stamped_from_spec():
    items = load_dataset_spec({
        "kind": "jsonl", "path": str(FIX), "name": "mini", "seed": 0,
        "contamination": "likely_contaminated",
    })
    assert all(i.meta["contamination"] == "likely_contaminated" for i in items)


def test_stamp_contamination_in_place():
    items = [TaskItem("a", "d", "p", "r", "g", {})]
    stamp_contamination(items, "fresh")
    assert items[0].meta["contamination"] == "fresh"


def _dated(id_, date):
    return TaskItem(id_, "d", "p", "r", "g", {"date": date} if date else {})


def test_apply_min_date_keeps_on_or_after_and_drops_undated():
    items = [_dated("old", "2024-01-01"), _dated("edge", "2025-06-01"),
             _dated("new", "2026-03-01"), _dated("undated", None)]
    kept = {i.id for i in apply_min_date(items, "2025-06-01")}
    assert kept == {"edge", "new"}  # boundary inclusive, undated dropped


def test_apply_min_date_custom_date_key():
    items = [TaskItem("x", "d", "p", "r", "g", {"contest_date": "2026-01-01"})]
    assert len(apply_min_date(items, "2025-01-01", date_key="contest_date")) == 1
