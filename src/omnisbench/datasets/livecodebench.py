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


def load_livecodebench(spec: dict) -> list[TaskItem]:
    from datasets import load_dataset

    from .loaders import _shuffle_limit  # deferred to avoid an import cycle

    ds = load_dataset(
        spec.get("hf_name", "livecodebench/code_generation_lite"),
        revision=spec.get("revision"),
        split=spec.get("split", "test"),
        trust_remote_code=spec.get("trust_remote_code", False),
    )
    items: list[TaskItem] = []
    for row in ds:
        item = map_row(dict(row), spec.get("prompt_prefix", ""))
        if item is not None:
            items.append(item)
    return _shuffle_limit(items, spec.get("limit"), spec.get("seed", 0))
