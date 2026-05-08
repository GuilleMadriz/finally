"""Service-test fixtures: isolated DB + a price cache with seeded prices."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db.connection import connect, reset_init_cache
from app.market import PriceCache


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test sqlite path, also exported as FINALLY_DB_PATH for code that uses default lookup."""
    reset_init_cache()
    path = tmp_path / "finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(path))
    return path


@pytest.fixture
def conn(db_path: Path):
    connection = connect(db_path)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def cache() -> PriceCache:
    """PriceCache pre-seeded with realistic prices for the default tickers."""
    c = PriceCache()
    seeds = {
        "AAPL": 190.0,
        "GOOGL": 175.0,
        "MSFT": 415.0,
        "AMZN": 178.0,
        "TSLA": 240.0,
        "NVDA": 880.0,
        "META": 480.0,
        "JPM": 195.0,
        "V": 275.0,
        "NFLX": 620.0,
    }
    for ticker, price in seeds.items():
        c.update(ticker, price)
    return c
