# SPDX-License-Identifier: Apache-2.0
"""Download and pin the OmnisBench v0 benchmark data.

Writes deterministic, reproducible JSONL files under data/:
  - data/humaneval.jsonl  — all 164 rows of openai/openai_humaneval (split: test)
  - data/gsm8k.jsonl      — first 200 rows (original order) of openai/gsm8k (config:
                            main, split: test)

Run: python scripts/prepare_datasets.py

This is the ONLY step in Step A that touches the network — it downloads from the
Hugging Face Hub (free), never an LLM API. If a download fails, this script prints
a clear error and exits non-zero rather than fabricating data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

GSM8K_LIMIT = 200


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def prepare_humaneval() -> int:
    from datasets import load_dataset

    ds = load_dataset("openai/openai_humaneval", split="test")
    rows = []
    for row in ds:
        rows.append({
            "id": row["task_id"],
            "prompt": row["prompt"],
            "reference": row["test"],
            "grader": "code_unittest",
            "meta": {"entry_point": row["entry_point"]},
        })
    _write_jsonl(DATA_DIR / "humaneval.jsonl", rows)
    return len(rows)


def _parse_gsm8k_answer(answer: str) -> str:
    # GSM8K's `answer` field ends with a rationale then "#### <number>".
    # e.g. "...\n#### 18" -> "18". Strip thousands-separator commas.
    tail = answer.rsplit("####", 1)[-1]
    return tail.strip().replace(",", "")


def prepare_gsm8k() -> int:
    from datasets import load_dataset

    ds = load_dataset("openai/gsm8k", "main", split="test")
    rows = []
    for i, row in enumerate(ds):
        if i >= GSM8K_LIMIT:
            break
        rows.append({
            "id": f"gsm8k-{i}",
            "prompt": row["question"],
            "reference": _parse_gsm8k_answer(row["answer"]),
            "grader": "numeric_match",
            "meta": {},
        })
    _write_jsonl(DATA_DIR / "gsm8k.jsonl", rows)
    return len(rows)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        n_humaneval = prepare_humaneval()
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero, don't fabricate
        print(f"ERROR: failed to prepare HumanEval dataset: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {DATA_DIR / 'humaneval.jsonl'} — {n_humaneval} rows")

    try:
        n_gsm8k = prepare_gsm8k()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to prepare GSM8K dataset: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {DATA_DIR / 'gsm8k.jsonl'} — {n_gsm8k} rows")

    return 0


if __name__ == "__main__":
    sys.exit(main())
