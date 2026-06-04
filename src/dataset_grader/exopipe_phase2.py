"""Discover grader catalog from exopipe phase2 lustre layout.

Layout (glob-style)::

    {root}/??h/*/Science_*/??MHz

- ``??h`` — LST hour directory (e.g. ``08h``)
- ``*`` — observation day (``YYYY-MM-DD``)
- ``Science_*`` — science run directory (any matching run implies the cell exists)
- ``??MHz`` — subband directory (e.g. ``55MHz``)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from dataset_grader.discovery import (
    DATE_PATTERN,
    FREQ_PATTERN,
    LST_PATTERN,
    _catalog_frame,
    normalize_day,
    normalize_frequency,
    normalize_lst,
)

DEFAULT_PHASE2_ROOT = Path("/lustre/pipeline/exopipe/phase2")
SCIENCE_DIR_PATTERN = re.compile(r"^Science_", re.IGNORECASE)


def discover_exopipe_phase2(root: Path | str = DEFAULT_PHASE2_ROOT) -> pd.DataFrame:
    """Scan phase2 tree and return a catalog of (day, lst, frequency) triples."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Phase2 root not found: {root}")

    rows: list[dict[str, str]] = []
    for lst_dir in sorted(root.iterdir()):
        if not lst_dir.is_dir():
            continue
        if not LST_PATTERN.match(lst_dir.name):
            continue
        lst = normalize_lst(lst_dir.name)
        for day_dir in sorted(lst_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            if not DATE_PATTERN.match(day_dir.name):
                continue
            day = normalize_day(day_dir.name)
            for science_dir in sorted(day_dir.iterdir()):
                if not science_dir.is_dir():
                    continue
                if not SCIENCE_DIR_PATTERN.match(science_dir.name):
                    continue
                for freq_dir in sorted(science_dir.iterdir()):
                    if not freq_dir.is_dir():
                        continue
                    if not FREQ_PATTERN.match(freq_dir.name):
                        continue
                    rows.append(
                        {
                            "day": day,
                            "lst": lst,
                            "frequency": normalize_frequency(freq_dir.name),
                        }
                    )

    return _catalog_frame(rows)
