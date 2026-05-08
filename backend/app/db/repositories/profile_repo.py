"""Profile (cash balance) repository."""

from __future__ import annotations

import sqlite3

from ..connection import DEFAULT_USER_ID


def get_profile(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> sqlite3.Row | None:
    """Return the profile row for ``user_id`` or None."""
    return conn.execute(
        "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
        (user_id,),
    ).fetchone()


def get_cash_balance(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> float:
    """Return the cash balance for ``user_id``. Raises if profile missing."""
    row = get_profile(conn, user_id)
    if row is None:
        raise LookupError(f"profile not found: {user_id}")
    return float(row["cash_balance"])


def set_cash_balance(
    conn: sqlite3.Connection, balance: float, user_id: str = DEFAULT_USER_ID
) -> None:
    """Overwrite the cash balance for ``user_id``."""
    conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (balance, user_id),
    )


def adjust_cash_balance(
    conn: sqlite3.Connection, delta: float, user_id: str = DEFAULT_USER_ID
) -> float:
    """Add ``delta`` (may be negative) to the cash balance and return the new value."""
    new_balance = get_cash_balance(conn, user_id) + delta
    set_cash_balance(conn, new_balance, user_id)
    return new_balance
