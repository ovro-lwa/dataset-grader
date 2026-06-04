"""Load reviewer names from a configuration file."""

from __future__ import annotations

import json
from pathlib import Path


def load_user_names(path: Path) -> list[str]:
    """Load unique reviewer names from JSON or a line-based text file.

    JSON may be a list of strings or an object with a ``users`` array.
    Text files use one name per line; ``#`` starts a comment.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Users file not found: {path}")

    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            names = [str(item) for item in raw]
        elif isinstance(raw, dict) and "users" in raw:
            names = [str(item) for item in raw["users"]]
        else:
            raise ValueError(
                f"Users file {path} must be a JSON list or object with a 'users' key"
            )
    else:
        names = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            names.append(stripped)

    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        trimmed = name.strip()
        if not trimmed:
            continue
        if trimmed in seen:
            continue
        seen.add(trimmed)
        unique.append(trimmed)

    if not unique:
        raise ValueError(f"No reviewer names defined in {path}")
    return unique


def ensure_allowed_user(name: str, allowed: list[str]) -> str:
    trimmed = name.strip()
    if trimmed not in allowed:
        raise ValueError(
            f"Reviewer {trimmed!r} is not in the configured list "
            f"({len(allowed)} name(s))"
        )
    return trimmed
