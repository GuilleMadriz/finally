"""Watchlist service tests, including market_source side-effect verification."""

from __future__ import annotations

import pytest

from app.market import MarketDataSource, PriceCache
from app.services import watchlist as watchlist_service


class FakeMarketSource(MarketDataSource):
    """In-memory MarketDataSource double that records add/remove calls."""

    def __init__(self) -> None:
        self.tickers: list[str] = []
        self.added: list[str] = []
        self.removed: list[str] = []

    async def start(self, tickers: list[str]) -> None:
        self.tickers = list(tickers)

    async def stop(self) -> None:
        self.tickers = []

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self.tickers:
            self.tickers.append(ticker)
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self.tickers:
            self.tickers.remove(ticker)
        self.removed.append(ticker)

    def get_tickers(self) -> list[str]:
        return list(self.tickers)


def test_normalize_ticker_uppercases_and_validates():
    assert watchlist_service.normalize_ticker("aapl") == "AAPL"
    assert watchlist_service.normalize_ticker(" GooGl ") == "GOOGL"
    with pytest.raises(watchlist_service.InvalidTicker):
        watchlist_service.normalize_ticker("")
    with pytest.raises(watchlist_service.InvalidTicker):
        watchlist_service.normalize_ticker("TOOLONG")
    with pytest.raises(watchlist_service.InvalidTicker):
        watchlist_service.normalize_ticker("ab-c")


def test_list_entries_returns_default_seed(db_path, cache: PriceCache):
    entries = watchlist_service.list_entries(cache)
    tickers = {e.ticker for e in entries}
    # Default seeded watchlist (order is implementation-dependent within a single seed batch)
    assert tickers == {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}
    assert all(e.price is not None for e in entries)


def test_list_entries_handles_missing_price(db_path):
    cache = PriceCache()  # no prices seeded
    entries = watchlist_service.list_entries(cache)
    assert entries[0].price is None
    assert entries[0].direction == "flat"


@pytest.mark.asyncio
async def test_add_invokes_market_source_and_inserts(db_path, cache: PriceCache):
    source = FakeMarketSource()
    normalized, added = await watchlist_service.add("pypl", source)
    assert normalized == "PYPL"
    assert added is True
    assert "PYPL" in source.added
    tickers = [e.ticker for e in watchlist_service.list_entries(cache)]
    assert "PYPL" in tickers


@pytest.mark.asyncio
async def test_add_idempotent_on_existing_ticker(db_path, cache: PriceCache):
    source = FakeMarketSource()
    normalized, added = await watchlist_service.add("AAPL", source)
    assert normalized == "AAPL"
    assert added is False  # already in seeded watchlist
    # add_ticker is still called so the source can ensure it's tracked
    assert source.added == ["AAPL"]


@pytest.mark.asyncio
async def test_remove_invokes_market_source_and_deletes(db_path, cache: PriceCache):
    source = FakeMarketSource()
    normalized, removed = await watchlist_service.remove("AAPL", source, cache)
    assert normalized == "AAPL"
    assert removed is True
    assert source.removed == ["AAPL"]
    assert cache.get("AAPL") is None
    tickers = [e.ticker for e in watchlist_service.list_entries(cache)]
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_remove_missing_ticker_returns_false(db_path, cache: PriceCache):
    source = FakeMarketSource()
    normalized, removed = await watchlist_service.remove("NOPE", source, cache)
    assert normalized == "NOPE"
    assert removed is False
    # remove_ticker still called to keep source state consistent
    assert source.removed == ["NOPE"]


@pytest.mark.asyncio
async def test_add_rejects_invalid_format(db_path, cache: PriceCache):
    source = FakeMarketSource()
    with pytest.raises(watchlist_service.InvalidTicker):
        await watchlist_service.add("ab-c", source)
