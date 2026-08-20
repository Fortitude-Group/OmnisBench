# SPDX-License-Identifier: Apache-2.0
from omnisbench.graders import GRADERS
from omnisbench.graders.stdin_tests import StdinTestsGrader, _normalize
from omnisbench.types import TaskItem

SUM = "```python\na, b = map(int, input().split())\nprint(a + b)\n```"


def _item(cases):
    return TaskItem("q1", "livecodebench", "prompt", cases, "livecodebench", {})


def test_livecodebench_grader_is_registered():
    assert "livecodebench" in GRADERS


def test_passes_when_all_cases_match():
    item = _item([{"input": "2 3\n", "output": "5\n"}, {"input": "10 20\n", "output": "30"}])
    assert StdinTestsGrader().score(SUM, item).passed


def test_fails_on_wrong_output():
    item = _item([{"input": "2 3\n", "output": "6"}])
    result = StdinTestsGrader().score(SUM, item)
    assert not result.passed
    assert result.detail["failed_case"] == 0


def test_fails_on_runtime_error():
    crashing = "```python\nprint(1 / 0)\n```"
    result = StdinTestsGrader().score(crashing, _item([{"input": "", "output": "x"}]))
    assert not result.passed
    assert result.detail["returncode"] != 0


def test_fails_when_no_cases():
    result = StdinTestsGrader().score(SUM, _item([]))
    assert not result.passed
    assert result.detail["reason"] == "no test cases"


def test_normalize_trims_trailing_whitespace_and_blank_lines():
    assert _normalize("5 \n\n\n") == "5"
    assert _normalize("a\r\nb\r\n") == "a\nb"
