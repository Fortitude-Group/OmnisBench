# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from omnisbench.datasets.loaders import load_dataset_spec, load_jsonl

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
