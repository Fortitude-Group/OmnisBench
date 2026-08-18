# SPDX-License-Identifier: Apache-2.0
from omnisbench.graders.matchers import GRADERS
from omnisbench.types import TaskItem


def _item(reference, grader, meta=None):
    return TaskItem("id", "ds", "prompt", reference, grader, meta or {})


def test_exact_match_trims_and_ignores_case():
    g = GRADERS["exact_match"]
    assert g.score("  Paris\n", _item("paris", "exact_match")).passed is True
    assert g.score("London", _item("paris", "exact_match")).passed is False


def test_numeric_match_extracts_last_number():
    g = GRADERS["numeric_match"]
    assert g.score("The answer is 18 apples.", _item("18", "numeric_match")).passed is True
    assert g.score("about 17", _item("18", "numeric_match")).passed is False
