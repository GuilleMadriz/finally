"""Watchlist service: DB persistence + market source coordination."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.db import DEFAULT_USER_ID, connect, transaction
from app.db.repositories import watchlist_repo
from app.market import MarketDataSource, PriceCache

_TICKER_RE = re.compile(r"^[A-Z0-9]{1,5}$")


class InvalidTicker(ValueError):  # noqa: N818
    """Raised when a ticker fails format validation."""


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    ticker: str
    price: float | None
    previous_price: float | None
    change: float | None
    change_percent: float | None
    direction: str  # "up" | "down" | "flat"


def normalize_ticker(ticker: str) -> str:
    """Uppercase + validate the ticker. Raises InvalidTicker on bad input."""
    if not ticker:
        raise InvalidTicker("ticker is required")
    cleaned = ticker.strip().upper()
    if not _TICKER_RE.match(cleaned):
        raise InvalidTicker(f"invalid ticker format: {ticker!r}")
    return cleaned


def list_entries(
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> list[WatchlistEntry]:
    """Return watchlist entries enriched with live prices from the cache."""
    conn = connect(db_path)
    try:
        tickers = watchlist_repo.list_tickers(conn, user_id=user_id)
    finally:
        conn.close()

    entries: list[WatchlistEntry] = []
    for ticker in tickers:
        update = cache.get(ticker)
        if update is None:
            entries.append(
                WatchlistEntry(
                    ticker=ticker,
                    price=None,
                    previous_price=None,
                    change=None,
                    change_percent=None,
                    direction="flat",
                )
            )
        else:
            entries.append(
                WatchlistEntry(
                    ticker=ticker,
                    price=update.price,
                    previous_price=update.previous_price,
                    change=update.change,
                    change_percent=update.change_percent,
                    direction=update.direction,
                )
            )
    return entries


async def add(
    ticker: str,
    market_source: MarketDataSource,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> tuple[str, bool]:
    """Add ticker to DB watchlist and the live market source.

    Returns ``(normalized_ticker, newly_added)``.
    Idempotent: if already in the watchlist, only ``add_ticker`` on the source
    is called (which is itself a no-op when the ticker is already tracked).
    """
    normalized = normalize_ticker(ticker)
    with transaction(db_path) as conn:
        newly_added = watchlist_repo.add_ticker(conn, normalized, user_id=user_id)
    await market_source.add_ticker(normalized)
    return normalized, newly_added


async def remove(
    ticker: str,
    market_source: MarketDataSource,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> tuple[str, bool]:
    """Remove ticker from the DB watchlist and the live market source.

    Returns ``(normalized_ticker, was_present)``. The market source's
    ``remove_ticker`` already evicts from the price cache, but we call
    ``cache.remove`` defensively in case implementations diverge.
    """
    normalized = normalize_ticker(ticker)
    with transaction(db_path) as conn:
        was_present = watchlist_repo.remove_ticker(conn, normalized, user_id=user_id)
    await market_source.remove_ticker(normalized)
    cache.remove(normalized)
    return normalized, was_present
