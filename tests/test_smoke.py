"""Programmatic smoke test for app wiring (no browser)."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from dataset_grader.aggregate import consensus_color
from dataset_grader.config import GraderConfig
from dataset_grader.db import GraderDatabase
from dataset_grader.discovery import discover_from_manifest
from dataset_grader.grids import GridGeometry, build_consensus_grid, build_personal_grid
from dataset_grader.grids import grades_by_dataset_from_df


def test_two_user_grading_flow(tmp_path: Path, example_manifest: Path):
    os.environ["GRADER_MANIFEST"] = str(example_manifest)
    users_file = example_manifest.parent / "users.json"
    config = GraderConfig(
        db_path=tmp_path / "smoke.sqlite",
        discovery_mode="manifest",
        manifest_path=example_manifest,
        data_root=None,
        users_path=users_file,
        host="127.0.0.1",
        port=8765,
    )
    db = GraderDatabase(config.db_path)
    db.initialize()
    catalog = discover_from_manifest(example_manifest)
    db.sync_datasets(catalog)
    days = db.list_days()
    assert "2024-12-28" in days

    alice = db.register_user("alice")
    bob = db.register_user("bob")
    day = "2024-12-28"
    datasets = db.datasets_for_day(day)
    geometry = GridGeometry.from_datasets(datasets)
    ds_id = int(datasets.iloc[0]["dataset_id"])

    db.upsert_grade(alice.id, ds_id, "pass")
    db.upsert_grade(bob.id, ds_id, "retry")

    personal = build_personal_grid(
        geometry, db.grades_for_user_day(alice.id, day), on_tap=lambda _: None
    )
    assert personal is not None

    grades_df = db.all_grades_for_day(day)
    by_ds = grades_by_dataset_from_df(grades_df)
    consensus = build_consensus_grid(geometry, by_ds)
    assert consensus is not None

    grades_for_cell = [g for _, g in by_ds[ds_id]]
    assert consensus_color(grades_for_cell) == "orange"
