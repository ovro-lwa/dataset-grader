"""Consensus coloring and hover text for aggregate grid cells."""

from __future__ import annotations

from collections.abc import Iterable

from dataset_grader.config import GRADE_VALUES

COLOR_GREY = "#9e9e9e"
COLOR_GREEN = "#4caf50"
COLOR_RED = "#e53935"
COLOR_ORANGE = "#fb8c00"

PERSONAL_COLORS = {
    "pass": "#a5d6a7",
    "fail": "#ef9a9a",
    "retry": "#ffcc80",
    None: "#e0e0e0",
}

CONSENSUS_COLORS = {
    "grey": COLOR_GREY,
    "green": COLOR_GREEN,
    "red": COLOR_RED,
    "orange": COLOR_ORANGE,
}


def consensus_color(grades: Iterable[str]) -> str:
    """Return semantic color key: grey, red, orange, or green."""
    grade_list = list(grades)
    if not grade_list:
        return "grey"
    if "fail" in grade_list:
        return "red"
    if "retry" in grade_list:
        return "orange"
    for g in grade_list:
        if g not in GRADE_VALUES:
            raise ValueError(f"Invalid grade {g!r}")
    return "green"


def consensus_fill(grades: Iterable[str]) -> str:
    return CONSENSUS_COLORS[consensus_color(grades)]


def format_hover_lines(entries: Iterable[tuple[str, str]]) -> str:
    """Build multi-line hover text from (user_name, grade) pairs."""
    lines = [f"{user}: {grade}" for user, grade in sorted(entries, key=lambda x: x[0])]
    return "\n".join(lines) if lines else "No grades yet"
