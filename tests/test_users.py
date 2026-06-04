import json
from pathlib import Path

import pytest

from dataset_grader.users import ensure_allowed_user, load_user_names


def test_load_users_json_list(tmp_path: Path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps(["alice", "bob", "alice"]))
    assert load_user_names(path) == ["alice", "bob"]


def test_load_users_json_object(tmp_path: Path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": ["x", "y"]}))
    assert load_user_names(path) == ["x", "y"]


def test_load_users_text_file(tmp_path: Path):
    path = tmp_path / "users.txt"
    path.write_text("# reviewers\nalice\n\nbob\n")
    assert load_user_names(path) == ["alice", "bob"]


def test_load_users_empty_raises(tmp_path: Path):
    path = tmp_path / "users.json"
    path.write_text("[]")
    with pytest.raises(ValueError, match="No reviewer"):
        load_user_names(path)


def test_ensure_allowed_user():
    allowed = ["alice", "bob"]
    assert ensure_allowed_user("alice", allowed) == "alice"
    with pytest.raises(ValueError, match="not in the configured"):
        ensure_allowed_user("eve", allowed)
