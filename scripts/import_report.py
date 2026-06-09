#!/usr/bin/env python3
"""Import reviewer grades from a team text report.

Example::

    python scripts/import_report.py \\
        --user gregg \\
        --report path/to/report.txt \\
        --db data/grader.sqlite

Report format (one grade per day/LST; all subbands get the same grade)::

    --- 01h (8/10 science ready) ---
      2024-12-18  [A]  Science ready
      2024-12-26  [D]  Bad imaging (2024-12-26)

Letter grades map to grader values: A → pass, B/C → retry, D → fail.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dataset_grader.db import GraderDatabase
from dataset_grader.report_import import apply_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import reviewer grades from a team text report.",
    )
    parser.add_argument(
        "--user",
        required=True,
        help="Reviewer name (e.g. gregg); registered if not already present.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Path to the text report file.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.cwd() / "data" / "grader.sqlite",
        help="SQLite database path (default: ./data/grader.sqlite).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and summarize without writing grades.",
    )
    args = parser.parse_args(argv)

    if not args.report.is_file():
        print(f"Report not found: {args.report}", file=sys.stderr)
        return 1

    db = GraderDatabase(args.db)
    db.initialize()
    result = apply_report(
        db,
        user_name=args.user,
        report=args.report,
        dry_run=args.dry_run,
    )

    action = "Would write" if args.dry_run else "Wrote"
    print(
        f"{action} {result.grades_written} grade(s) for {result.user_name!r} "
        f"across {result.cells_applied} day/LST cell(s) "
        f"({len(result.entries)} report line(s))."
    )
    if result.missing:
        print("No datasets found for:", file=sys.stderr)
        for day, lst in result.missing:
            print(f"  {day} {lst}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
