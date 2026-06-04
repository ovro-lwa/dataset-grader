from pathlib import Path

import pandas as pd
import pytest

from dataset_grader.discovery import (
    discover_from_directory,
    discover_from_manifest,
    normalize_frequency,
    normalize_lst,
)


def test_normalize_frequency():
    assert normalize_frequency(74) == "74MHz"
    assert normalize_frequency("82MHz") == "82MHz"
    assert normalize_frequency("55") == "55MHz"


def test_normalize_lst():
    assert normalize_lst("8") == "08h"
    assert normalize_lst("09h") == "09h"


def test_discover_from_manifest(example_manifest: Path):
    df = discover_from_manifest(example_manifest)
    assert list(df.columns) == ["day", "lst", "frequency"]
    assert len(df) == 6
    assert df.iloc[0]["day"] == "2024-12-28"


def test_discover_from_directory(tmp_path: Path):
    root = tmp_path / "data"
    (root / "2024-12-28" / "08h").mkdir(parents=True)
    (root / "2024-12-28" / "08h" / "74MHz.png").write_bytes(b"x")
    (root / "2024-12-28" / "08h" / "82MHz.fits").write_bytes(b"y")
    (root / "2024-12-28" / "08h" / "readme.txt").write_bytes(b"z")
    df = discover_from_directory(root)
    assert len(df) == 2
    assert set(df["frequency"]) == {"74MHz", "82MHz"}


def test_discover_manifest_missing_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("day,lst\n2024-01-01,08h\n")
    with pytest.raises(ValueError, match="frequency"):
        discover_from_manifest(path)
