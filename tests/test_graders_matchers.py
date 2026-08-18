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


def test_exact_match_is_strict_no_suffix_false_positive():
    g = GRADERS["exact_match"]
    # suffix match must NOT pass (regression for the removed endswith clause)
    assert g.score("lambda", _item("a", "exact_match")).passed is False
    assert g.score("not paris", _item("paris", "exact_match")).passed is False
    # true equality still passes (trim + case-insensitive)
    assert g.score("  Paris\n", _item("paris", "exact_match")).passed is True


def test_exact_match_extracts_choice_letter():
    g = GRADERS["exact_match"]
    meta = {"choices": ["A", "B", "C", "D"]}
    assert g.score("I think the answer is B.", _item("B", "exact_match", meta)).passed is True
    assert g.score("The answer is C", _item("B", "exact_match", meta)).passed is False
    # last stated valid letter wins
    assert g.score("Between A and B, I choose B.", _item("B", "exact_match", meta)).passed is True
    # no valid choice letter present -> fail
    assert g.score("I am not sure.", _item("B", "exact_match", meta)).passed is False
