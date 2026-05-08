"""Tests for trades_repo."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories import trades_repo


class TestTradesRepo:
    def test_record_buy(self, conn: sqlite3.Connection):
        tid = trades_repo.record_trade(conn, "AAPL", "buy", 10.0, 190.0)
        assert isinstance(tid, str) and len(tid) == 32
        rows = trades_repo.list_trades(conn)
        assert len(rows) == 1
        assert rows[0]["side"] == "buy"
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["quantity"] == 10.0
        assert rows[0]["price"] == 190.0

    def test_record_sell(self, conn: sqlite3.Connection):
        trades_repo.record_trade(conn, "AAPL", "sell", 5.0, 200.0)
        rows = trades_repo.list_trades(conn)
        assert rows[0]["side"] == "sell"

    def test_record_invalid_side(self, conn: sqlite3.Connection):
        with pytest.raises(ValueError):
            trades_repo.record_trade(conn, "AAPL", "hold", 1.0, 1.0)

    def test_list_trades_newest_first(self, conn: sqlite3.Connection):
        trades_repo.record_trade(
            conn, "AAPL", "buy", 1.0, 100.0, executed_at="2026-01-01T00:00:00+00:00"
        )
        trades_repo.record_trade(
            conn, "AAPL", "sell", 1.0, 110.0, executed_at="2026-01-02T00:00:00+00:00"
        )
        rows = trades_repo.list_trades(conn)
        assert rows[0]["side"] == "sell"
        assert rows[1]["side"] == "buy"

    def test_list_trades_limit(self, conn: sqlite3.Connection):
        for i in range(5):
            trades_repo.record_trade(
                conn,
                "AAPL",
                "buy",
                1.0,
                100.0 + i,
                executed_at=f"2026-01-0{i + 1}T00:00:00+00:00",
            )
        rows = trades_repo.list_trades(conn, limit=2)
        assert len(rows) == 2
        assert rows[0]["price"] == 104.0
        assert rows[1]["price"] == 103.0
