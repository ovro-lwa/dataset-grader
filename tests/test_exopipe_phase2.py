from pathlib import Path

import pandas as pd

from dataset_grader.exopipe_phase2 import discover_exopipe_phase2


def _write_phase2_tree(root: Path) -> None:
    """Mirror ovro-lwa-portal phase2 layout: {lst}h/{day}/Science_*/{freq}MHz/."""
    run = root / "08h" / "2025-01-11" / "Science_20260527_173819"
    (run / "55MHz" / "I").mkdir(parents=True)
    (run / "82MHz" / "I").mkdir(parents=True)
    run2 = root / "09h" / "2025-01-12" / "Science_20260528_120000"
    (run2 / "74MHz").mkdir(parents=True)
    # ignored: wrong day format
    (root / "08h" / "not-a-day" / "Science_x" / "55MHz").mkdir(parents=True)
    # ignored: no Science_ prefix
    (root / "08h" / "2025-01-13" / "Run_20260527" / "55MHz").mkdir(parents=True)


def test_discover_exopipe_phase2(tmp_path: Path):
    _write_phase2_tree(tmp_path)
    df = discover_exopipe_phase2(tmp_path)
    assert len(df) == 3
    assert set(df.columns) == {"day", "lst", "frequency"}
    assert (
        df[
            (df["day"] == "2025-01-11")
            & (df["lst"] == "08h")
            & (df["frequency"] == "55MHz")
        ].shape[0]
        == 1
    )


def test_discover_deduplicates_multiple_science_runs(tmp_path: Path):
    root = tmp_path / "phase2"
    for name in ("Science_aaa", "Science_bbb"):
        (root / "08h" / "2025-01-11" / name / "55MHz").mkdir(parents=True)
    df = discover_exopipe_phase2(root)
    assert len(df) == 1


def test_discover_empty_root(tmp_path: Path):
    root = tmp_path / "empty"
    root.mkdir()
    df = discover_exopipe_phase2(root)
    assert df.empty
    assert list(df.columns) == ["day", "lst", "frequency"]
