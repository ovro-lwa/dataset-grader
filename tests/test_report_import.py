from pathlib import Path

import pandas as pd

from dataset_grader.db import GraderDatabase
from dataset_grader.report_import import ReportEntry, apply_report, parse_report

SAMPLE_REPORT = """\
--- 00h (0/1 science ready) ---
  2024-12-18  [D]  Outlier: rejected by Phase 3 two-pass co-add
--- 01h (8/10 science ready) ---
  2024-12-18  [A]  Science ready
  2024-12-19  [A]  Science ready
  2024-12-26  [D]  Bad imaging (2024-12-26)
  2024-12-27  [B]  Needs another look
"""


def test_parse_report():
    entries = parse_report(SAMPLE_REPORT)
    assert len(entries) == 5
    assert entries[0] == ReportEntry(
        day="2024-12-18", lst="00h", report_grade="D", grade="fail"
    )
    assert entries[1].day == "2024-12-18"
    assert entries[1].lst == "01h"
    assert entries[1].grade == "pass"
    assert entries[-1].report_grade == "B"
    assert entries[-1].grade == "retry"


def test_apply_report_all_subbands(db: GraderDatabase):
    catalog = pd.DataFrame(
        [
            {"day": "2024-12-18", "lst": "01h", "frequency": "55MHz"},
            {"day": "2024-12-18", "lst": "01h", "frequency": "59MHz"},
            {"day": "2024-12-18", "lst": "00h", "frequency": "55MHz"},
        ]
    )
    db.sync_datasets(catalog)
    result = apply_report(
        db,
        user_name="gregg",
        report=SAMPLE_REPORT,
    )
    user = db.get_user_by_name("gregg")
    assert user is not None
    assert result.grades_written == 3
    assert result.cells_applied == 2
    assert result.missing == [("2024-12-19", "01h"), ("2024-12-26", "01h"), ("2024-12-27", "01h")]

    day18 = db.datasets_for_day("2024-12-18")
    ids_01h = day18.loc[day18["lst"] == "01h", "dataset_id"].tolist()
    ids_00h = day18.loc[day18["lst"] == "00h", "dataset_id"].tolist()
    grades = db.grades_for_user_day(user.id, "2024-12-18")
    assert all(grades[ds_id] == "pass" for ds_id in ids_01h)
    assert all(grades[ds_id] == "fail" for ds_id in ids_00h)


def test_apply_report_dry_run(db: GraderDatabase):
    catalog = pd.DataFrame(
        [{"day": "2024-12-18", "lst": "01h", "frequency": "55MHz"}]
    )
    db.sync_datasets(catalog)
    result = apply_report(
        db,
        user_name="gregg",
        report="--- 01h (1/1 science ready) ---\n  2024-12-18  [A]  Science ready\n",
        dry_run=True,
    )
    assert result.grades_written == 1
    assert db.get_user_by_name("gregg") is None
    assert db.all_grades_for_day("2024-12-18").empty


def test_apply_report_from_file(db: GraderDatabase, tmp_path: Path):
    catalog = pd.DataFrame(
        [{"day": "2024-12-18", "lst": "01h", "frequency": "55MHz"}]
    )
    db.sync_datasets(catalog)
    report_path = tmp_path / "report.txt"
    report_path.write_text(
        "--- 01h (1/1 science ready) ---\n  2024-12-18  [C]  Retry\n"
    )
    result = apply_report(db, user_name="gregg", report=report_path)
    user = db.get_user_by_name("gregg")
    ds_id = int(db.datasets_for_day("2024-12-18").iloc[0]["dataset_id"])
    assert result.grades_written == 1
    assert db.grades_for_user_day(user.id, "2024-12-18")[ds_id] == "retry"
