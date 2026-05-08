"""Tests for connection helper, lazy init, and seeding."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db.connection import (
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST,
    connect,
    get_db_path,
    init_db,
    reset_init_cache,
    transaction,
)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row["name"] for row in rows}


class TestInitAndSeed:
    def test_init_creates_all_tables(self, db_path: Path):
        init_db(db_path)
        with sqlite3.connect(db_path) as raw:
            raw.row_factory = sqlite3.Row
            tables = _table_names(raw)
        expected = {
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        }
        assert expected.issubset(tables)

    def test_seeds_default_profile(self, conn: sqlite3.Connection):
        row = conn.execute(
            "SELECT id, cash_balance FROM users_profile WHERE id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()
        assert row is not None
        assert row["cash_balance"] == 10000.0

    def test_seeds_default_watchlist(self, conn: sqlite3.Connection):
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
            (DEFAULT_USER_ID,),
        ).fetchall()
        tickers = {row["ticker"] for row in rows}
        assert tickers == set(DEFAULT_WATCHLIST)
        assert len(rows) == 10

    def test_init_is_idempotent(self, db_path: Path):
        init_db(db_path)
        init_db(db_path)
        reset_init_cache()
        init_db(db_path)
        with sqlite3.connect(db_path) as raw:
            raw.row_factory = sqlite3.Row
            (count,) = raw.execute(
                "SELECT COUNT(*) FROM watchlist WHERE user_id = 'default'"
            ).fetchone()
            (profile_count,) = raw.execute(
                "SELECT COUNT(*) FROM users_profile"
            ).fetchone()
        assert count == 10
        assert profile_count == 1

    def test_connect_creates_parent_dir(self, tmp_path: Path):
        reset_init_cache()
        nested = tmp_path / "deep" / "nested" / "finally.db"
        c = connect(nested)
        try:
            assert nested.exists()
        finally:
            c.close()

    def test_connect_returns_row_factory(self, conn: sqlite3.Connection):
        row = conn.execute("SELECT 1 AS one").fetchone()
        assert row["one"] == 1

    def test_foreign_keys_enabled(self, conn: sqlite3.Connection):
        (fk,) = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk == 1


class TestPathResolution:
    def test_get_db_path_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("FINALLY_DB_PATH", raising=False)
        path = get_db_path()
        assert path.name == "finally.db"
        assert path.parent.name == "db"

    def test_get_db_path_env_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        target = tmp_path / "custom.db"
        monkeypatch.setenv("FINALLY_DB_PATH", str(target))
        assert get_db_path() == target


class TestTransaction:
    def test_commits_on_success(self, db_path: Path):
        with transaction(db_path) as conn:
            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (5000.0, DEFAULT_USER_ID),
            )
        with sqlite3.connect(db_path) as raw:
            raw.row_factory = sqlite3.Row
            row = raw.execute(
                "SELECT cash_balance FROM users_profile WHERE id = 'default'"
            ).fetchone()
        assert row["cash_balance"] == 5000.0

    def test_rolls_back_on_exception(self, db_path: Path):
        with pytest.raises(RuntimeError):
            with transaction(db_path) as conn:
                conn.execute(
                    "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                    (1.0, DEFAULT_USER_ID),
                )
                raise RuntimeError("boom")
        with sqlite3.connect(db_path) as raw:
            raw.row_factory = sqlite3.Row
            row = raw.execute(
                "SELECT cash_balance FROM users_profile WHERE id = 'default'"
            ).fetchone()
        assert row["cash_balance"] == 10000.0


class TestUniqueConstraints:
    def test_watchlist_unique_user_ticker(self, conn: sqlite3.Connection):
        # Default seed already inserted AAPL.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                ("dup", DEFAULT_USER_ID, "AAPL", "2026-01-01T00:00:00+00:00"),
            )

    def test_positions_unique_user_ticker(self, conn: sqlite3.Connection):
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("p1", DEFAULT_USER_ID, "AAPL", 10, 100.0, "2026-01-01T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("p2", DEFAULT_USER_ID, "AAPL", 5, 200.0, "2026-01-01T00:00:00+00:00"),
            )

    def test_trades_side_check(self, conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("t1", DEFAULT_USER_ID, "AAPL", "hold", 1, 1.0, "2026-01-01T00:00:00+00:00"),
            )

    def test_chat_role_check(self, conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("c1", DEFAULT_USER_ID, "system", "x", None, "2026-01-01T00:00:00+00:00"),
            )
