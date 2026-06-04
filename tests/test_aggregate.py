import pytest

from dataset_grader.aggregate import (
    consensus_color,
    consensus_fill,
    format_hover_lines,
)


@pytest.mark.parametrize(
    "grades,expected",
    [
        ([], "grey"),
        (["pass"], "green"),
        (["pass", "pass"], "green"),
        (["retry"], "orange"),
        (["pass", "retry"], "orange"),
        (["fail"], "red"),
        (["pass", "fail"], "red"),
        (["retry", "fail"], "red"),
    ],
)
def test_consensus_color(grades, expected):
    assert consensus_color(grades) == expected


def test_consensus_fill_maps_to_hex():
    assert consensus_fill(["fail"]).startswith("#")


def test_format_hover_lines_sorted():
    text = format_hover_lines([("bob", "pass"), ("alice", "retry")])
    assert text.splitlines()[0].startswith("alice")


def test_format_hover_empty():
    assert format_hover_lines([]) == "No grades yet"
