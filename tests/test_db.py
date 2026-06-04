from pathlib import Path

import pandas as pd
import pytest

from dataset_grader.db import GraderDatabase


@pytest.fixture
def db(tmp_path: Path) -> GraderDatabase:
    database = GraderDatabase(tmp_path / "test.sqlite")
    database.initialize()
    return database


def test_register_and_grade(db: GraderDatabase):
    user = db.register_user("alice")
    catalog = pd.DataFrame(
        [{"day": "2024-12-28", "lst": "08h", "frequency": "74MHz"}]
    )
    db.sync_datasets(catalog)
    datasets = db.datasets_for_day("2024-12-28")
    ds_id = int(datasets.iloc[0]["dataset_id"])
    db.upsert_grade(user.id, ds_id, "pass")
    grades = db.grades_for_user_day(user.id, "2024-12-28")
    assert grades[ds_id] == "pass"
    db.upsert_grade(user.id, ds_id, "fail")
    assert db.grades_for_user_day(user.id, "2024-12-28")[ds_id] == "fail"


def test_sync_idempotent(db: GraderDatabase):
    catalog = pd.DataFrame(
        [
            {"day": "2024-12-28", "lst": "08h", "frequency": "74MHz"},
            {"day": "2024-12-28", "lst": "08h", "frequency": "82MHz"},
        ]
    )
    db.sync_datasets(catalog)
    db.sync_datasets(catalog)
    assert len(db.datasets_for_day("2024-12-28")) == 2


def test_all_grades_for_day(db: GraderDatabase):
    alice = db.register_user("alice")
    bob = db.register_user("bob")
    catalog = pd.DataFrame(
        [{"day": "2024-12-28", "lst": "08h", "frequency": "74MHz"}]
    )
    db.sync_datasets(catalog)
    ds_id = int(db.datasets_for_day("2024-12-28").iloc[0]["dataset_id"])
    db.upsert_grade(alice.id, ds_id, "pass")
    db.upsert_grade(bob.id, ds_id, "retry")
    df = db.all_grades_for_day("2024-12-28")
    assert len(df) == 2
    assert set(df["grade"]) == {"pass", "retry"}


def test_register_empty_name(db: GraderDatabase):
    with pytest.raises(ValueError):
        db.register_user("   ")
