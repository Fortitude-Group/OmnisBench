# SPDX-License-Identifier: Apache-2.0
from omnisbench.graders.code_unittest import GRADERS, extract_code
from omnisbench.types import TaskItem

TEST_HARNESS = "assert candidate(2, 3) == 5\n"
HUMANEVAL_HARNESS = "def check(candidate):\n    assert candidate(2, 3) == 5\n"


def _item():
    # No entry_point in meta: exercises the old/plain behavior — the program is
    # just `candidate + reference`, with no appended check(...) call.
    return TaskItem("id", "ds", "prompt", TEST_HARNESS, "code_unittest", {})


def _humaneval_item(entry_point: str = "add"):
    # HumanEval-shaped: reference defines `check(candidate)` but never calls it;
    # meta.entry_point tells the grader which function name to pass to check(...).
    return TaskItem("id", "ds", "prompt", HUMANEVAL_HARNESS, "code_unittest",
                    {"entry_point": entry_point})


def test_extract_code_from_fenced_block():
    text = "Sure:\n```python\ndef candidate(a, b):\n    return a + b\n```\nDone."
    assert "return a + b" in extract_code(text)
    assert "Sure:" not in extract_code(text)


def test_correct_code_passes():
    g = GRADERS["code_unittest"]
    resp = "```python\ndef candidate(a, b):\n    return a + b\n```"
    assert g.score(resp, _item()).passed is True


def test_wrong_code_fails():
    g = GRADERS["code_unittest"]
    resp = "```python\ndef candidate(a, b):\n    return a - b\n```"
    assert g.score(resp, _item()).passed is False


def test_infinite_loop_times_out_and_fails():
    g = GRADERS["code_unittest"]
    resp = "```python\ndef candidate(a, b):\n    while True:\n        pass\n```"
    assert g.score(resp, _item()).passed is False


def test_humaneval_entry_point_correct_code_passes():
    # Without appending check(entry_point), this program would exit 0 (no assertion
    # ever runs) even for a WRONG candidate — the bug this test guards against.
    g = GRADERS["code_unittest"]
    resp = "```python\ndef add(a, b):\n    return a + b\n```"
    assert g.score(resp, _humaneval_item("add")).passed is True


def test_humaneval_entry_point_wrong_code_fails():
    g = GRADERS["code_unittest"]
    resp = "```python\ndef add(a, b):\n    return a - b\n```"
    assert g.score(resp, _humaneval_item("add")).passed is False
