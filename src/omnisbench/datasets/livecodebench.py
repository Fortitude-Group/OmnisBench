# SPDX-License-Identifier: Apache-2.0
"""LiveCodeBench loader.

LiveCodeBench problems come from competitive-programming sites and each carries a
release date, which is what makes a contamination-resistant "fresh" split possible:
combine this loader with ``min_date`` in the dataset spec to keep only problems
published after the model pool's training cutoff.

This loader covers the stdin/stdout problem type (input on stdin, answer on stdout),
graded by the ``livecodebench`` grader. Functional problems (implement a named
function) are skipped for now and are the next step. Private test cases are included
only when they arrive as plain JSON; LiveCodeBench's compressed/pickled private-case
encoding is deliberately not un-pickled here, so untrusted data is never unpickled.
"""
from __future__ import annotations

import json

from ..types import TaskItem

_STDIN_INSTRUCTION = (
    "Read the input from standard input and write the answer to standard output. "
    "Return the full program in a single ```python code block.\n\n"
)


def parse_test_cases(raw: object) -> list[dict]:
    """Return ``[{input, output, testtype}]`` from a LiveCodeBench test-case field.

    Accepts a decoded list or a plain JSON string. Anything that is not plain JSON
    (LiveCodeBench's compressed private-case blobs) yields an empty list rather than
    being decoded, so grading falls back to the cases we can read safely.
    """
    if isinstance(raw, list):
        data: object = raw
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return []
        try:
            data = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return []
    else:
        return []
    out: list[dict] = []
    if isinstance(data, list):
        for c in data:
            if isinstance(c, dict) and "input" in c and "output" in c:
                out.append({
                    "input": c["input"],
                    "output": c["output"],
                    "testtype": c.get("testtype", "stdin"),
                })
    return out


def stdin_cases(row: dict) -> list[dict]:
    """All stdin-type test cases for a row, as ``[{input, output}]``."""
    cases = parse_test_cases(row.get("public_test_cases")) + parse_test_cases(row.get("private_test_cases"))
    return [
        {"input": c["input"], "output": c["output"]}
        for c in cases if c.get("testtype", "stdin") == "stdin"
    ]


def map_row(row: dict, prompt_prefix: str = "") -> TaskItem | None:
    """Map one LiveCodeBench row to a TaskItem, or None if it has no stdin cases."""
    cases = stdin_cases(row)
    if not cases:
        return None
    qid = str(row.get("question_id") or row.get("question_title") or row.get("question_content", ""))[:200]
    prompt = f"{prompt_prefix}{_STDIN_INSTRUCTION}{row.get('question_content', '')}"
    starter = row.get("starter_code") or ""
    if starter:
        prompt += f"\n\nStarter code:\n```python\n{starter}\n```"
    return TaskItem(
        id=qid,
        dataset="livecodebench",
        prompt=prompt,
        reference=cases,
        grader="livecodebench",
        meta={"date": str(row.get("contest_date", ""))[:10], "platform": row.get("platform", "")},
    )


_DEFAULT_FILES = [f"test{n}.jsonl" if n else "test.jsonl" for n in ("", 2, 3, 4, 5, 6)]


def select_items(rows: list[dict], spec: dict) -> list[TaskItem]:
    """Map raw LiveCodeBench rows to TaskItems, then filter by date, then cap.

    Order matters: ``min_date`` must be applied BEFORE ``limit``, otherwise the cap
    samples from all dates first and leaves only a handful of fresh problems. Kept as
    a pure function so the ordering is unit-testable without a network download.
    """
    from .loaders import _shuffle_limit, apply_min_date  # deferred to avoid a cycle

    items: list[TaskItem] = []
    for row in rows:
        item = map_row(row, spec.get("prompt_prefix", ""))
        if item is not None:
            items.append(item)
    min_date = spec.get("min_date")
    if min_date:
        items = apply_min_date(items, min_date, spec.get("date_key", "date"))
    return _shuffle_limit(items, spec.get("limit"), spec.get("seed", 0))


def load_livecodebench(spec: dict) -> list[TaskItem]:
    """Load LiveCodeBench by downloading its raw JSONL release files from the HF hub.

    The published dataset is script-based, which recent `datasets` refuses to run, so
    we pull the ``testN.jsonl`` files directly with ``huggingface_hub`` and dedupe
    problems by id. The contamination tag is stamped by the caller (``load_dataset_spec``).
    """
    from huggingface_hub import hf_hub_download

    repo = spec.get("hf_name", "livecodebench/code_generation_lite")
    files = spec.get("hf_files", _DEFAULT_FILES)
    by_id: dict[object, dict] = {}
    for fname in files:
        path = hf_hub_download(repo, fname, repo_type="dataset", revision=spec.get("revision"))
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                by_id[row.get("question_id", len(by_id))] = row
    return select_items(list(by_id.values()), spec)
