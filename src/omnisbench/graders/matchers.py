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
        choices = item.meta.get("choices")
        if choices:
            valid = {str(c).strip().upper() for c in choices}
            want = str(item.reference).strip().upper()
            found = [
                c.upper()
                for c in re.findall(r"\b([A-Za-z])\b", response_text)
                if c.upper() in valid
            ]
            got = found[-1] if found else ""
            passed = got != "" and got == want
            return GradeResult(
                passed, 1.0 if passed else 0.0,
                {"got": got, "want": want, "choices": sorted(valid)},
            )
        got = response_text.strip().casefold()
        want = str(item.reference).strip().casefold()
        passed = got == want
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
