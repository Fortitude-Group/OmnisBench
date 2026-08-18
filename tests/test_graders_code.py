# SPDX-License-Identifier: Apache-2.0
from omnisbench.graders.code_unittest import GRADERS, extract_code
from omnisbench.types import TaskItem

TEST_HARNESS = "assert candidate(2, 3) == 5\n"


def _item():
    return TaskItem("id", "ds", "prompt", TEST_HARNESS, "code_unittest",
                    {"entry_point": "candidate"})


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
