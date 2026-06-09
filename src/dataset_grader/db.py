"""SQLite persistence for users, datasets, and grades."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pandas as pd

from dataset_grader.config import GRADE_VALUES


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class Dataset:
    id: int
    day: str
    lst: str
    frequency: str


class GraderDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day TEXT NOT NULL,
                    lst TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    UNIQUE(day, lst, frequency)
                );

                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    dataset_id INTEGER NOT NULL,
                    grade TEXT NOT NULL CHECK(grade IN ('pass', 'fail', 'retry')),
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, dataset_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def register_user(self, name: str) -> User:
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("Name cannot be empty")
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (name, created_at) VALUES (?, ?)",
                (trimmed, now),
            )
            row = conn.execute(
                "SELECT id, name FROM users WHERE name = ?", (trimmed,)
            ).fetchone()
        if row is None:
            raise RuntimeError(f"Failed to register user {trimmed!r}")
        return User(id=int(row["id"]), name=str(row["name"]))

    def get_user_by_name(self, name: str) -> User | None:
        trimmed = name.strip()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name FROM users WHERE name = ?", (trimmed,)
            ).fetchone()
        if row is None:
            return None
        return User(id=int(row["id"]), name=str(row["name"]))

    def sync_datasets(self, catalog: pd.DataFrame) -> int:
        """Upsert datasets from discovery catalog. Returns number of rows touched."""
        required = ("day", "lst", "frequency")
        missing = set(required) - set(catalog.columns)
        if missing:
            raise ValueError(f"Catalog missing columns: {sorted(missing)}")
        rows = catalog[list(required)].drop_duplicates()
        count = 0
        with self._connect() as conn:
            for day, lst, frequency in rows.itertuples(index=False, name=None):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO datasets (day, lst, frequency)
                    VALUES (?, ?, ?)
                    """,
                    (str(day), str(lst), str(frequency)),
                )
                count += 1
        return count

    def list_days(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT day FROM datasets ORDER BY day"
            ).fetchall()
        return [str(r["day"]) for r in rows]

    def dataset_ids_for_day_lst(self, day: str, lst: str) -> list[int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM datasets
                WHERE day = ? AND lst = ?
                ORDER BY frequency
                """,
                (day, lst),
            ).fetchall()
        return [int(r["id"]) for r in rows]

    def datasets_for_day(self, day: str) -> pd.DataFrame:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, day, lst, frequency
                FROM datasets
                WHERE day = ?
                ORDER BY lst, frequency
                """,
                (day,),
            ).fetchall()
        return pd.DataFrame(
            [
                {
                    "dataset_id": int(r["id"]),
                    "day": str(r["day"]),
                    "lst": str(r["lst"]),
                    "frequency": str(r["frequency"]),
                }
                for r in rows
            ]
        )

    def delete_grade(self, user_id: int, dataset_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM grades WHERE user_id = ? AND dataset_id = ?",
                (user_id, dataset_id),
            )

    def upsert_grade(self, user_id: int, dataset_id: int, grade: str) -> None:
        if grade not in GRADE_VALUES:
            raise ValueError(f"Invalid grade {grade!r}")
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO grades (user_id, dataset_id, grade, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, dataset_id) DO UPDATE SET
                    grade = excluded.grade,
                    updated_at = excluded.updated_at
                """,
                (user_id, dataset_id, grade, now),
            )

    def grades_for_user_day(self, user_id: int, day: str) -> dict[int, str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT g.dataset_id, g.grade
                FROM grades g
                JOIN datasets d ON d.id = g.dataset_id
                WHERE g.user_id = ? AND d.day = ?
                """,
                (user_id, day),
            ).fetchall()
        return {int(r["dataset_id"]): str(r["grade"]) for r in rows}

    def all_datasets(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, day, lst, frequency
                FROM datasets
                ORDER BY day, lst, frequency
                """
            ).fetchall()
        return pd.DataFrame(
            [
                {
                    "dataset_id": int(r["id"]),
                    "day": str(r["day"]),
                    "lst": str(r["lst"]),
                    "frequency": str(r["frequency"]),
                }
                for r in rows
            ]
        )

    def all_grades(self) -> pd.DataFrame:
        """Return columns: dataset_id, user_name, grade."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT g.dataset_id, u.name AS user_name, g.grade
                FROM grades g
                JOIN users u ON u.id = g.user_id
                ORDER BY g.dataset_id, u.name
                """
            ).fetchall()
        return pd.DataFrame(
            [
                {
                    "dataset_id": int(r["dataset_id"]),
                    "user_name": str(r["user_name"]),
                    "grade": str(r["grade"]),
                }
                for r in rows
            ]
        )

    def all_grades_for_day(self, day: str) -> pd.DataFrame:
        """Return columns: dataset_id, user_name, grade."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT g.dataset_id, u.name AS user_name, g.grade
                FROM grades g
                JOIN datasets d ON d.id = g.dataset_id
                JOIN users u ON u.id = g.user_id
                WHERE d.day = ?
                ORDER BY g.dataset_id, u.name
                """,
                (day,),
            ).fetchall()
        return pd.DataFrame(
            [
                {
                    "dataset_id": int(r["dataset_id"]),
                    "user_name": str(r["user_name"]),
                    "grade": str(r["grade"]),
                }
                for r in rows
            ]
        )
