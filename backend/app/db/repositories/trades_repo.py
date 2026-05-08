"""Trades repository (append-only log)."""

from __future__ import annotations

import sqlite3

from ..connection import DEFAULT_USER_ID, new_id, utc_now_iso


def record_trade(
    conn: sqlite3.Connection,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
    executed_at: str | None = None,
) -> str:
    """Append a trade to the log. Returns the trade id."""
    if side not in ("buy", "sell"):
        raise ValueError(f"invalid side: {side}")
    trade_id = new_id()
    conn.execute(
        """
        INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (trade_id, user_id, ticker, side, quantity, price, executed_at or utc_now_iso()),
    )
    return trade_id


def list_trades(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """Return trades for ``user_id`` newest first."""
    sql = """
        SELECT id, user_id, ticker, side, quantity, price, executed_at
        FROM trades
        WHERE user_id = ?
        ORDER BY executed_at DESC, id DESC
    """
    params: tuple = (user_id,)
    if limit is not None:
        sql += " LIMIT ?"
        params = (user_id, limit)
    return conn.execute(sql, params).fetchall()
