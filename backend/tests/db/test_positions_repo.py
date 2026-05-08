"""Tests for positions_repo."""

from __future__ import annotations

import sqlite3

from app.db.repositories import positions_repo


class TestPositionsRepo:
    def test_no_positions_initially(self, conn: sqlite3.Connection):
        assert positions_repo.list_positions(conn) == []
        assert positions_repo.get_position(conn, "AAPL") is None

    def test_upsert_creates(self, conn: sqlite3.Connection):
        positions_repo.upsert_position(conn, "AAPL", 10.0, 190.0)
        row = positions_repo.get_position(conn, "AAPL")
        assert row["quantity"] == 10.0
        assert row["avg_cost"] == 190.0

    def test_upsert_updates(self, conn: sqlite3.Connection):
        positions_repo.upsert_position(conn, "AAPL", 10.0, 190.0)
        positions_repo.upsert_position(conn, "AAPL", 15.0, 195.0)
        row = positions_repo.get_position(conn, "AAPL")
        assert row["quantity"] == 15.0
        assert row["avg_cost"] == 195.0
        assert len(positions_repo.list_positions(conn)) == 1

    def test_list_positions_ordered(self, conn: sqlite3.Connection):
        positions_repo.upsert_position(conn, "MSFT", 5.0, 420.0)
        positions_repo.upsert_position(conn, "AAPL", 10.0, 190.0)
        positions_repo.upsert_position(conn, "GOOGL", 2.0, 175.0)
        rows = positions_repo.list_positions(conn)
        tickers = [r["ticker"] for r in rows]
        assert tickers == ["AAPL", "GOOGL", "MSFT"]

    def test_delete_position(self, conn: sqlite3.Connection):
        positions_repo.upsert_position(conn, "AAPL", 10.0, 190.0)
        deleted = positions_repo.delete_position(conn, "AAPL")
        assert deleted is True
        assert positions_repo.get_position(conn, "AAPL") is None

    def test_delete_missing(self, conn: sqlite3.Connection):
        assert positions_repo.delete_position(conn, "ZZZ") is False
