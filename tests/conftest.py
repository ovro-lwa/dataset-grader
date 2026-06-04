from pathlib import Path

import pytest


@pytest.fixture
def example_manifest() -> Path:
    return Path(__file__).resolve().parents[1] / "example" / "manifest.csv"
