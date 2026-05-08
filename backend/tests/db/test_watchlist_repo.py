"""Tests for watchlist_repo."""

from __future__ import annotations

import sqlite3

from app.db.connection import DEFAULT_WATCHLIST
from app.db.repositories import watchlist_repo


class TestWatchlistRepo:
    def test_list_tickers_returns_seed(self, conn: sqlite3.Connection):
        tickers = watchlist_repo.list_tickers(conn)
        assert set(tickers) == set(DEFAULT_WATCHLIST)
        assert len(tickers) == 10

    def test_add_new_ticker(self, conn: sqlite3.Connection):
        added = watchlist_repo.add_ticker(conn, "PYPL")
        assert added is True
        assert "PYPL" in watchlist_repo.list_tickers(conn)

    def test_add_existing_ticker_is_noop(self, conn: sqlite3.Connection):
        added = watchlist_repo.add_ticker(conn, "AAPL")
        assert added is False
        assert watchlist_repo.list_tickers(conn).count("AAPL") == 1

    def test_remove_ticker(self, conn: sqlite3.Connection):
        removed = watchlist_repo.remove_ticker(conn, "AAPL")
        assert removed is True
        assert "AAPL" not in watchlist_repo.list_tickers(conn)

    def test_remove_missing_ticker(self, conn: sqlite3.Connection):
        removed = watchlist_repo.remove_ticker(conn, "ZZZ")
        assert removed is False

    def test_has_ticker(self, conn: sqlite3.Connection):
        assert watchlist_repo.has_ticker(conn, "AAPL")
        assert not watchlist_repo.has_ticker(conn, "ZZZ")
