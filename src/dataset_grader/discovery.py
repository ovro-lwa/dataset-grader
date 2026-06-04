"""Discover dataset catalog from manifest CSV or directory layout."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from dataset_grader.config import GraderConfig

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LST_PATTERN = re.compile(r"^\d{2}h$", re.IGNORECASE)
FREQ_PATTERN = re.compile(r"^\d+MHz$", re.IGNORECASE)


def normalize_frequency(value: str | float | int) -> str:
    """Normalize frequency to ``74MHz`` style labels."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        mhz = int(value) if float(value).is_integer() else float(value)
        if isinstance(mhz, float):
            return f"{mhz:g}MHz"
        return f"{mhz}MHz"
    text = str(value).strip()
    if text.lower().endswith("mhz"):
        num = text[:-3].strip()
        if num.isdigit():
            return f"{int(num)}MHz"
        return text
    if text.replace(".", "", 1).isdigit():
        num = float(text)
        if num.is_integer():
            return f"{int(num)}MHz"
        return f"{num:g}MHz"
    return text


def normalize_lst(value: str) -> str:
    text = str(value).strip()
    if text.lower().endswith("h") and text[:-1].isdigit():
        return f"{int(text[:-1]):02d}h"
    if text.isdigit():
        return f"{int(text):02d}h"
    return text


def normalize_day(value: str) -> str:
    text = str(value).strip()
    if not DATE_PATTERN.match(text):
        raise ValueError(f"Invalid day {value!r}, expected YYYY-MM-DD")
    return text


def _catalog_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["day", "lst", "frequency"])
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["day", "lst", "frequency"])
    return df.sort_values(["day", "lst", "frequency"]).reset_index(drop=True)


def discover_from_manifest(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    df = pd.read_csv(path)
    col_map = {c.lower(): c for c in df.columns}
    for required in ("day", "lst", "frequency"):
        if required not in col_map:
            raise ValueError(
                f"Manifest {path} must include column {required!r}, got {list(df.columns)}"
            )
    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "day": normalize_day(row[col_map["day"]]),
                "lst": normalize_lst(row[col_map["lst"]]),
                "frequency": normalize_frequency(row[col_map["frequency"]]),
            }
        )
    return _catalog_frame(rows)


def discover_from_directory(root: Path) -> pd.DataFrame:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Data root not found: {root}")
    rows: list[dict[str, str]] = []
    for day_dir in sorted(root.iterdir()):
        if not day_dir.is_dir():
            continue
        day = day_dir.name
        if not DATE_PATTERN.match(day):
            continue
        for lst_dir in sorted(day_dir.iterdir()):
            if not lst_dir.is_dir():
                continue
            lst = lst_dir.name
            if not LST_PATTERN.match(lst):
                continue
            lst = normalize_lst(lst)
            for path in sorted(lst_dir.iterdir()):
                if path.is_dir():
                    continue
                frequency = path.stem
                if not FREQ_PATTERN.match(frequency):
                    continue
                rows.append(
                    {
                        "day": day,
                        "lst": lst,
                        "frequency": normalize_frequency(frequency),
                    }
                )
    return _catalog_frame(rows)


def discover_catalog(config: GraderConfig) -> pd.DataFrame:
    if config.discovery_mode == "manifest":
        if config.manifest_path is None:
            raise ValueError(
                "GRADER_MANIFEST must be set when GRADER_DISCOVERY=manifest"
            )
        return discover_from_manifest(config.manifest_path)
    if config.discovery_mode == "exopipe_phase2":
        from dataset_grader.exopipe_phase2 import (
            DEFAULT_PHASE2_ROOT,
            discover_exopipe_phase2,
        )

        root = config.data_root or DEFAULT_PHASE2_ROOT
        return discover_exopipe_phase2(root)
    if config.data_root is None:
        raise ValueError(
            "GRADER_DATA_ROOT must be set when GRADER_DISCOVERY=directory"
        )
    return discover_from_directory(config.data_root)
