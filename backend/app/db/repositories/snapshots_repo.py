"""Portfolio snapshots repository."""

from __future__ import annotations

import sqlite3

from ..connection import DEFAULT_USER_ID, new_id, utc_now_iso


def record_snapshot(
    conn: sqlite3.Connection,
    total_value: float,
    user_id: str = DEFAULT_USER_ID,
    recorded_at: str | None = None,
) -> str:
    """Append a portfolio value snapshot. Returns the snapshot id."""
    snap_id = new_id()
    conn.execute(
        """
        INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
        VALUES (?, ?, ?, ?)
        """,
        (snap_id, user_id, total_value, recorded_at or utc_now_iso()),
    )
    return snap_id


def list_snapshots(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """Return snapshots for ``user_id`` ordered oldest to newest."""
    sql = """
        SELECT id, user_id, total_value, recorded_at
        FROM portfolio_snapshots
        WHERE user_id = ?
        ORDER BY recorded_at
    """
    params: tuple = (user_id,)
    if limit is not None:
        sql = """
            SELECT id, user_id, total_value, recorded_at
            FROM (
                SELECT id, user_id, total_value, recorded_at
                FROM portfolio_snapshots
                WHERE user_id = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            )
            ORDER BY recorded_at
        """
        params = (user_id, limit)
    return conn.execute(sql, params).fetchall()
