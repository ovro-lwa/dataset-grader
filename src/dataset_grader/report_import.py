"""Parse team text reports and import grades for a reviewer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from dataset_grader.db import GraderDatabase, User

REPORT_GRADE_MAP = {
    "A": "pass",
    "B": "retry",
    "C": "retry",
    "D": "fail",
}

_LST_HEADER = re.compile(r"^---\s+(\d+h)\s+\(", re.IGNORECASE)
_DAY_LINE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s+\[([ABCD])\]", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ReportEntry:
    day: str
    lst: str
    report_grade: str
    grade: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    user_name: str
    entries: list[ReportEntry]
    grades_written: int
    cells_applied: int
    missing: list[tuple[str, str]]


def parse_report(text: str) -> list[ReportEntry]:
    """Parse a team report into (day, lst, grade) entries."""
    entries: list[ReportEntry] = []
    current_lst: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        header = _LST_HEADER.match(line)
        if header:
            current_lst = header.group(1).lower()
            continue
        if current_lst is None:
            continue
        match = _DAY_LINE.match(line)
        if match is None:
            continue
        report_grade = match.group(2).upper()
        grade = REPORT_GRADE_MAP[report_grade]
        entries.append(
            ReportEntry(
                day=match.group(1),
                lst=current_lst,
                report_grade=report_grade,
                grade=grade,
            )
        )
    return entries


def apply_report(
    db: GraderDatabase,
    *,
    user_name: str,
    report: str | Path,
    dry_run: bool = False,
) -> ImportResult:
    """Register the reviewer if needed and apply report grades to all subbands."""
    trimmed = user_name.strip()
    if not trimmed:
        raise ValueError("Name cannot be empty")
    text = Path(report).read_text() if isinstance(report, Path) else report
    entries = parse_report(text)
    if dry_run:
        user = User(id=-1, name=trimmed)
    else:
        user = db.get_user_by_name(trimmed) or db.register_user(trimmed)

    grades_written = 0
    cells_applied = 0
    missing: list[tuple[str, str]] = []
    for entry in entries:
        dataset_ids = db.dataset_ids_for_day_lst(entry.day, entry.lst)
        if not dataset_ids:
            missing.append((entry.day, entry.lst))
            continue
        cells_applied += 1
        if dry_run:
            grades_written += len(dataset_ids)
            continue
        for dataset_id in dataset_ids:
            db.upsert_grade(user.id, dataset_id, entry.grade)
            grades_written += 1
    return ImportResult(
        user_name=user.name,
        entries=entries,
        grades_written=grades_written,
        cells_applied=cells_applied,
        missing=missing,
    )
