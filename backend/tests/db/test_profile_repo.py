"""Tests for profile_repo."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories import profile_repo


class TestProfileRepo:
    def test_get_profile_default(self, conn: sqlite3.Connection):
        row = profile_repo.get_profile(conn)
        assert row["id"] == "default"
        assert row["cash_balance"] == 10000.0

    def test_get_cash_balance(self, conn: sqlite3.Connection):
        assert profile_repo.get_cash_balance(conn) == 10000.0

    def test_get_cash_balance_missing(self, conn: sqlite3.Connection):
        with pytest.raises(LookupError):
            profile_repo.get_cash_balance(conn, user_id="ghost")

    def test_set_cash_balance(self, conn: sqlite3.Connection):
        profile_repo.set_cash_balance(conn, 7500.0)
        assert profile_repo.get_cash_balance(conn) == 7500.0

    def test_adjust_cash_balance(self, conn: sqlite3.Connection):
        new_value = profile_repo.adjust_cash_balance(conn, -250.0)
        assert new_value == 9750.0
        assert profile_repo.get_cash_balance(conn) == 9750.0

        new_value = profile_repo.adjust_cash_balance(conn, 500.0)
        assert new_value == 10250.0
