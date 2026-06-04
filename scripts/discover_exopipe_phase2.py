#!/usr/bin/env python3
"""Scan exopipe phase2 lustre tree and write a grader manifest CSV.

Path pattern::

    {root}/??h/*/Science_*/??MHz

Example::

    python scripts/discover_exopipe_phase2.py \\
        --root /lustre/pipeline/exopipe/phase2 \\
        --output data/phase2_manifest.csv

Then point the grader at the manifest::

    export GRADER_MANIFEST=/path/to/phase2_manifest.csv
    ./scripts/serve.sh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without install: repo root on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from dataset_grader.exopipe_phase2 import DEFAULT_PHASE2_ROOT, discover_exopipe_phase2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover (day, LST, frequency) cells from exopipe phase2 directories.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_PHASE2_ROOT,
        help=f"Phase2 pipeline root (default: {DEFAULT_PHASE2_ROOT})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output manifest CSV path (columns: day, lst, frequency)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print catalog to stdout instead of writing a file",
    )
    args = parser.parse_args(argv)

    catalog = discover_exopipe_phase2(args.root)
    if catalog.empty:
        print(f"No cells found under {args.root}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(catalog.to_csv(index=False))
        print(f"# {len(catalog)} row(s)", file=sys.stderr)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(args.output, index=False)
    print(f"Wrote {len(catalog)} row(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
