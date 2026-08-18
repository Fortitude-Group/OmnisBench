# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from ..types import GradeResult, TaskItem

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


@runtime_checkable
class Grader(Protocol):
    def score(self, response_text: str, item: TaskItem) -> GradeResult: ...


class ExactMatchGrader:
    def score(self, response_text: str, item: TaskItem) -> GradeResult:
        got = response_text.strip().casefold()
        want = str(item.reference).strip().casefold()
        passed = got == want or got.endswith(want)
        return GradeResult(passed, 1.0 if passed else 0.0, {"got": response_text.strip()})


class NumericMatchGrader:
    def score(self, response_text: str, item: TaskItem) -> GradeResult:
        matches = _NUM.findall(response_text.replace(",", ""))
        if not matches:
            return GradeResult(False, 0.0, {"reason": "no number found"})
        got = float(matches[-1])
        want = float(item.reference)
        passed = abs(got - want) < 1e-6
        return GradeResult(passed, 1.0 if passed else 0.0, {"got": got, "want": want})


GRADERS: dict[str, Grader] = {
    "exact_match": ExactMatchGrader(),
    "numeric_match": NumericMatchGrader(),
}
