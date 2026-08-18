# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re

from ..types import GradeResult, TaskItem
from .matchers import GRADERS
from .sandbox import run_python

_FENCE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    m = _FENCE.search(text)
    return m.group(1) if m else text


class CodeUnittestGrader:
    def __init__(self, timeout_s: float = 10.0):
        self._timeout_s = timeout_s

    def score(self, response_text: str, item: TaskItem) -> GradeResult:
        candidate = extract_code(response_text)
        entry_point = item.meta.get("entry_point")
        if entry_point:
            program = f"{candidate}\n\n{item.reference}\n\ncheck({entry_point})\n"
        else:
            program = f"{candidate}\n\n{item.reference}\n"
        rc, output = run_python(program, self._timeout_s)
        passed = rc == 0
        return GradeResult(passed, 1.0 if passed else 0.0, {"returncode": rc, "output": output[-2000:]})


GRADERS["code_unittest"] = CodeUnittestGrader()
