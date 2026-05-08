"""Shared fixtures for db tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db.connection import connect, reset_init_cache


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fresh SQLite path per test."""
    reset_init_cache()
    return tmp_path / "finally.db"


@pytest.fixture
def conn(db_path: Path):
    """Open connection to a freshly initialized DB."""
    connection = connect(db_path)
    try:
        yield connection
    finally:
        connection.close()
