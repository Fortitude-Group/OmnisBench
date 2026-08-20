# SPDX-License-Identifier: Apache-2.0
from omnisbench.datasets.livecodebench import map_row, parse_test_cases, stdin_cases


def test_parse_from_json_string():
    cases = parse_test_cases('[{"input":"1\\n","output":"1\\n","testtype":"stdin"}]')
    assert cases == [{"input": "1\n", "output": "1\n", "testtype": "stdin"}]


def test_parse_passthrough_list():
    assert parse_test_cases([{"input": "a", "output": "b"}])[0]["output"] == "b"


def test_parse_returns_empty_on_non_json_or_missing():
    # LiveCodeBench's compressed private blobs are not un-pickled; they yield [].
    assert parse_test_cases("H4sIA-not-json-blob") == []
    assert parse_test_cases(None) == []
    assert parse_test_cases(123) == []
    assert parse_test_cases("") == []


def test_stdin_cases_filters_out_functional():
    row = {"public_test_cases":
           '[{"input":"1","output":"2","testtype":"stdin"},'
           '{"input":"x","output":"y","testtype":"functional"}]'}
    assert stdin_cases(row) == [{"input": "1", "output": "2"}]


def test_map_row_builds_taskitem_with_date_and_reference():
    row = {
        "question_id": "abc123",
        "question_content": "Add two numbers",
        "contest_date": "2025-07-01T00:00:00",
        "platform": "leetcode",
        "public_test_cases": '[{"input":"1 2","output":"3","testtype":"stdin"}]',
    }
    item = map_row(row)
    assert item is not None
    assert item.id == "abc123"
    assert item.grader == "livecodebench"
    assert item.meta["date"] == "2025-07-01"
    assert item.reference == [{"input": "1 2", "output": "3"}]
    assert "Add two numbers" in item.prompt


def test_map_row_skips_functional_only_problems():
    row = {"question_id": "f1", "question_content": "...",
           "public_test_cases": '[{"input":"x","output":"y","testtype":"functional"}]'}
    assert map_row(row) is None
