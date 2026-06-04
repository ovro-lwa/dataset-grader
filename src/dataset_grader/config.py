"""Environment-driven configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

GRADE_VALUES = ("pass", "fail", "retry")
DISCOVERY_MODES = ("manifest", "directory", "exopipe_phase2")


def next_grade(current: str | None) -> str | None:
    """Advance one step: unset → pass → fail → retry → unset."""
    if current not in GRADE_VALUES:
        return GRADE_VALUES[0]
    if current == GRADE_VALUES[-1]:
        return None
    idx = GRADE_VALUES.index(current)
    return GRADE_VALUES[idx + 1]


def _env_path(name: str, default: str | None = None) -> Path | None:
    raw = os.environ.get(name, default)
    if raw is None or raw == "":
        return None
    return Path(raw).expanduser()


@dataclass(frozen=True, slots=True)
class GraderConfig:
    db_path: Path
    discovery_mode: str
    manifest_path: Path | None
    data_root: Path | None
    users_path: Path
    host: str
    port: int

    @classmethod
    def from_env(cls) -> GraderConfig:
        mode = os.environ.get("GRADER_DISCOVERY", "manifest").strip().lower()
        if mode not in DISCOVERY_MODES:
            raise ValueError(
                f"GRADER_DISCOVERY must be one of {DISCOVERY_MODES}, got {mode!r}"
            )
        db_default = str(Path.cwd() / "data" / "grader.sqlite")
        users_default = str(Path.cwd() / "config" / "users.json")
        return cls(
            db_path=_env_path("GRADER_DB_PATH", db_default) or Path(db_default),
            discovery_mode=mode,
            manifest_path=_env_path("GRADER_MANIFEST"),
            data_root=_env_path("GRADER_DATA_ROOT"),
            users_path=_env_path("GRADER_USERS_FILE", users_default)
            or Path(users_default),
            host=os.environ.get("GRADER_HOST", "127.0.0.1"),
            port=int(os.environ.get("GRADER_PORT", "8765")),
        )
