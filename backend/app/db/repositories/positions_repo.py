"""Positions repository (one row per ticker per user)."""

from __future__ import annotations

import sqlite3

from ..connection import DEFAULT_USER_ID, new_id, utc_now_iso


def get_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> sqlite3.Row | None:
    """Return the position row for ``ticker`` or None."""
    return conn.execute(
        """
        SELECT id, user_id, ticker, quantity, avg_cost, updated_at
        FROM positions
        WHERE user_id = ? AND ticker = ?
        """,
        (user_id, ticker),
    ).fetchone()


def list_positions(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID
) -> list[sqlite3.Row]:
    """Return all positions for ``user_id``."""
    return conn.execute(
        """
        SELECT id, user_id, ticker, quantity, avg_cost, updated_at
        FROM positions
        WHERE user_id = ?
        ORDER BY ticker
        """,
        (user_id,),
    ).fetchall()


def upsert_position(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    avg_cost: float,
    user_id: str = DEFAULT_USER_ID,
) -> None:
    """Create or replace the position for ``ticker``."""
    now = utc_now_iso()
    existing = get_position(conn, ticker, user_id)
    if existing is None:
        conn.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id(), user_id, ticker, quantity, avg_cost, now),
        )
    else:
        conn.execute(
            """
            UPDATE positions
            SET quantity = ?, avg_cost = ?, updated_at = ?
            WHERE user_id = ? AND ticker = ?
            """,
            (quantity, avg_cost, now, user_id, ticker),
        )


def delete_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Delete the position for ``ticker``. Returns True if a row was deleted."""
    cursor = conn.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    return cursor.rowcount > 0
