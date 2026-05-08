"""Chat messages repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..connection import DEFAULT_USER_ID, new_id, utc_now_iso


def append_message(
    conn: sqlite3.Connection,
    role: str,
    content: str,
    actions: dict[str, Any] | list[Any] | None = None,
    user_id: str = DEFAULT_USER_ID,
    created_at: str | None = None,
) -> str:
    """Append a chat message. Returns the message id."""
    if role not in ("user", "assistant"):
        raise ValueError(f"invalid role: {role}")
    msg_id = new_id()
    actions_json = json.dumps(actions) if actions is not None else None
    conn.execute(
        """
        INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (msg_id, user_id, role, content, actions_json, created_at or utc_now_iso()),
    )
    return msg_id


def list_messages(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """Return messages for ``user_id`` ordered oldest first.

    When ``limit`` is set, returns the most recent ``limit`` messages, still
    ordered oldest first (suitable for prompt history).
    """
    if limit is None:
        return conn.execute(
            """
            SELECT id, user_id, role, content, actions, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY created_at, id
            """,
            (user_id,),
        ).fetchall()
    return conn.execute(
        """
        SELECT id, user_id, role, content, actions, created_at
        FROM (
            SELECT id, user_id, role, content, actions, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        )
        ORDER BY created_at, id
        """,
        (user_id, limit),
    ).fetchall()


def parse_actions(row: sqlite3.Row) -> dict[str, Any] | list[Any] | None:
    """Decode the ``actions`` JSON column from a row, or None."""
    raw = row["actions"]
    return json.loads(raw) if raw else None
