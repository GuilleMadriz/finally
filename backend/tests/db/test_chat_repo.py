"""Tests for chat_repo."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories import chat_repo


class TestChatRepo:
    def test_append_user_message(self, conn: sqlite3.Connection):
        mid = chat_repo.append_message(conn, "user", "Hello")
        assert isinstance(mid, str) and len(mid) == 32
        rows = chat_repo.list_messages(conn)
        assert len(rows) == 1
        assert rows[0]["role"] == "user"
        assert rows[0]["content"] == "Hello"
        assert rows[0]["actions"] is None

    def test_append_assistant_with_actions(self, conn: sqlite3.Connection):
        actions = {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}]}
        chat_repo.append_message(conn, "assistant", "Bought 10 AAPL.", actions=actions)
        rows = chat_repo.list_messages(conn)
        decoded = chat_repo.parse_actions(rows[0])
        assert decoded == actions

    def test_invalid_role(self, conn: sqlite3.Connection):
        with pytest.raises(ValueError):
            chat_repo.append_message(conn, "system", "nope")

    def test_list_messages_oldest_first(self, conn: sqlite3.Connection):
        chat_repo.append_message(
            conn, "user", "first", created_at="2026-01-01T00:00:00+00:00"
        )
        chat_repo.append_message(
            conn, "assistant", "second", created_at="2026-01-02T00:00:00+00:00"
        )
        chat_repo.append_message(
            conn, "user", "third", created_at="2026-01-03T00:00:00+00:00"
        )
        rows = chat_repo.list_messages(conn)
        assert [r["content"] for r in rows] == ["first", "second", "third"]

    def test_list_messages_limit_returns_recent_oldest_first(self, conn: sqlite3.Connection):
        for i in range(5):
            chat_repo.append_message(
                conn,
                "user",
                f"msg{i}",
                created_at=f"2026-01-0{i + 1}T00:00:00+00:00",
            )
        rows = chat_repo.list_messages(conn, limit=2)
        contents = [r["content"] for r in rows]
        assert contents == ["msg3", "msg4"]

    def test_parse_actions_none(self, conn: sqlite3.Connection):
        chat_repo.append_message(conn, "user", "plain")
        rows = chat_repo.list_messages(conn)
        assert chat_repo.parse_actions(rows[0]) is None
