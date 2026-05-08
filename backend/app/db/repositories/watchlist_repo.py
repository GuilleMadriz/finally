"""Watchlist repository."""

from __future__ import annotations

import sqlite3

from ..connection import DEFAULT_USER_ID, new_id, utc_now_iso


def list_tickers(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Return all watched tickers for ``user_id`` ordered by added_at."""
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    ).fetchall()
    return [row["ticker"] for row in rows]


def add_ticker(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Add ``ticker`` to the watchlist. Returns True if newly added, False if already present."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at)
        VALUES (?, ?, ?, ?)
        """,
        (new_id(), user_id, ticker, utc_now_iso()),
    )
    return cursor.rowcount > 0


def remove_ticker(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Remove ``ticker`` from the watchlist. Returns True if a row was deleted."""
    cursor = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    return cursor.rowcount > 0


def has_ticker(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Return True if ``ticker`` is in the watchlist."""
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    return row is not None
