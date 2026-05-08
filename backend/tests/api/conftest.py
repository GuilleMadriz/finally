"""Test app for portfolio + watchlist routes — minimal FastAPI wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.portfolio import router as portfolio_router
from app.api.watchlist import router as watchlist_router
from app.db.connection import connect, reset_init_cache
from app.market import MarketDataSource, PriceCache


class FakeMarketSource(MarketDataSource):
    def __init__(self, cache: PriceCache, default_price: float = 100.0) -> None:
        self.cache = cache
        self.tickers: list[str] = []
        self.added: list[str] = []
        self.removed: list[str] = []
        self.default_price = default_price

    async def start(self, tickers: list[str]) -> None:
        self.tickers = list(tickers)

    async def stop(self) -> None:
        self.tickers = []

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self.tickers:
            self.tickers.append(ticker)
        self.added.append(ticker)
        # mimic real source seeding the cache
        self.cache.update(ticker, self.default_price)

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self.tickers:
            self.tickers.remove(ticker)
        self.removed.append(ticker)
        self.cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self.tickers)


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    reset_init_cache()
    path = tmp_path / "finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(path))
    return path


@pytest.fixture
def cache(db_path: Path) -> PriceCache:
    """Cache pre-populated with prices for the seeded watchlist."""
    # Touch DB so seed runs
    connect(db_path).close()
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


@pytest.fixture
def market_source(cache: PriceCache) -> FakeMarketSource:
    return FakeMarketSource(cache)


@pytest.fixture
def client(cache: PriceCache, market_source: FakeMarketSource) -> TestClient:
    app = FastAPI()
    app.state.price_cache = cache
    app.state.market_source = market_source
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    return TestClient(app)
