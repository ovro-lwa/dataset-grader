from pathlib import Path

import pytest

from dataset_grader.db import GraderDatabase


@pytest.fixture
def example_manifest() -> Path:
    return Path(__file__).resolve().parents[1] / "example" / "manifest.csv"


@pytest.fixture
def db(tmp_path: Path) -> GraderDatabase:
    database = GraderDatabase(tmp_path / "test.sqlite")
    database.initialize()
    return database
