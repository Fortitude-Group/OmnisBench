# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ..types import GradeResult, TaskItem
from .code_unittest import extract_code
from .matchers import GRADERS
from .sandbox import run_python_io


def _normalize(text: str) -> str:
    """Normalise program output for comparison: unify newlines, strip trailing
    whitespace on each line, and drop trailing blank lines. This is the usual
    tolerance for competitive-programming stdout without accepting wrong answers.
    """
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


class StdinTestsGrader:
    """Grade a solution against stdin/stdout test cases.

    ``item.reference`` is a list of ``{"input": str, "output": str}`` cases (built by
    the LiveCodeBench loader). The extracted code is run once per case with the case
    input on stdin, and every case must exit cleanly and match the expected output.
    This runs untrusted model code in the same subprocess sandbox as the unit-test
    grader; the isolation caveats in the repo security warning apply.
    """

    def __init__(self, timeout_s: float = 8.0, max_cases: int = 40):
        self._timeout_s = timeout_s
        self._max_cases = max_cases

    def score(self, response_text: str, item: TaskItem) -> GradeResult:
        code = extract_code(response_text)
        cases = item.reference
        if not isinstance(cases, list) or not cases:
            return GradeResult(False, 0.0, {"reason": "no test cases"})
        checked = cases[: self._max_cases]
        for i, case in enumerate(checked):
            stdin = str(case.get("input", ""))
            want = _normalize(str(case.get("output", "")))
            rc, out, err = run_python_io(code, stdin, self._timeout_s)
            if rc != 0:
                return GradeResult(False, 0.0,
                                   {"failed_case": i, "returncode": rc, "stderr": err[-500:]})
            if _normalize(out) != want:
                return GradeResult(False, 0.0,
                                   {"failed_case": i, "got": out[-500:], "want": want[-500:]})
        return GradeResult(True, 1.0, {"cases_passed": len(checked)})


GRADERS["livecodebench"] = StdinTestsGrader()
