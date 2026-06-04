import pytest

from dataset_grader.config import next_grade


@pytest.mark.parametrize(
    "current,expected",
    [
        (None, "pass"),
        ("pass", "fail"),
        ("fail", "retry"),
        ("retry", None),
        ("invalid", "pass"),
    ],
)
def test_next_grade(current, expected):
    assert next_grade(current) == expected


def test_delete_grade_clears_cell(tmp_path):
    import pandas as pd

    from dataset_grader.db import GraderDatabase

    database = GraderDatabase(tmp_path / "test.sqlite")
    database.initialize()
    user = database.register_user("alice")
    catalog = pd.DataFrame(
        [{"day": "2024-12-28", "lst": "08h", "frequency": "74MHz"}]
    )
    database.sync_datasets(catalog)
    ds_id = int(database.datasets_for_day("2024-12-28").iloc[0]["dataset_id"])
    database.upsert_grade(user.id, ds_id, "pass")
    database.delete_grade(user.id, ds_id)
    assert database.grades_for_user_day(user.id, "2024-12-28") == {}
