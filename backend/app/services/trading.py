"""Trade execution and portfolio valuation.

These functions are sync; route handlers wrap them with ``asyncio.to_thread``.
The chat endpoint reuses :func:`execute_trade` for LLM-driven trades.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.db import DEFAULT_USER_ID, transaction
from app.db.repositories import (
    positions_repo,
    profile_repo,
    snapshots_repo,
    trades_repo,
)
from app.market import PriceCache


class TradeError(ValueError):
    """Base class for trade validation failures."""


class InsufficientCash(TradeError):  # noqa: N818  (domain naming preferred over `Error` suffix)
    """Raised when buy cost exceeds available cash."""


class InsufficientShares(TradeError):  # noqa: N818
    """Raised when sell quantity exceeds the held position."""


class UnknownTicker(TradeError):  # noqa: N818
    """Raised when a ticker has no current price in the cache."""


@dataclass(frozen=True, slots=True)
class TradeResult:
    """Outcome of a successful trade execution."""

    ticker: str
    side: str
    quantity: float
    price: float
    cash_balance: float
    realized_pnl: float  # zero for buys; sell proceeds minus cost basis sold
    snapshot_total_value: float


def execute_trade(
    cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> TradeResult:
    """Execute a market order at the cache's current price.

    Validates side, positive quantity, ticker availability, and (per side)
    cash or share sufficiency. Atomic: cash, position, trade row, and snapshot
    are written in a single transaction.
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise TradeError(f"invalid side: {side}")
    if quantity <= 0:
        raise TradeError("quantity must be positive")

    ticker = ticker.upper()
    price = cache.get_price(ticker)
    if price is None:
        raise UnknownTicker(f"no price available for {ticker}")

    with transaction(db_path) as conn:
        if side == "buy":
            realized = 0.0
            cash_balance = _apply_buy(conn, ticker, quantity, price, user_id)
        else:
            cash_balance, realized = _apply_sell(conn, ticker, quantity, price, user_id)

        trades_repo.record_trade(
            conn, ticker=ticker, side=side, quantity=quantity, price=price, user_id=user_id
        )
        total_value = _total_portfolio_value(conn, cache, user_id)
        snapshots_repo.record_snapshot(conn, total_value=total_value, user_id=user_id)

    return TradeResult(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        cash_balance=cash_balance,
        realized_pnl=round(realized, 4),
        snapshot_total_value=total_value,
    )


def _apply_buy(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    price: float,
    user_id: str,
) -> float:
    cost = quantity * price
    balance = profile_repo.get_cash_balance(conn, user_id)
    if balance < cost:
        raise InsufficientCash(
            f"insufficient cash: need {cost:.2f}, have {balance:.2f}"
        )

    existing = positions_repo.get_position(conn, ticker, user_id)
    if existing is None:
        new_qty = quantity
        new_avg = price
    else:
        prev_qty = float(existing["quantity"])
        prev_avg = float(existing["avg_cost"])
        new_qty = prev_qty + quantity
        new_avg = (prev_qty * prev_avg + quantity * price) / new_qty

    positions_repo.upsert_position(
        conn, ticker=ticker, quantity=new_qty, avg_cost=new_avg, user_id=user_id
    )
    return profile_repo.adjust_cash_balance(conn, -cost, user_id)


def _apply_sell(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    price: float,
    user_id: str,
) -> tuple[float, float]:
    existing = positions_repo.get_position(conn, ticker, user_id)
    if existing is None:
        raise InsufficientShares(f"no position in {ticker}")
    held = float(existing["quantity"])
    if quantity > held + 1e-9:
        raise InsufficientShares(
            f"insufficient shares: need {quantity}, hold {held}"
        )
    avg_cost = float(existing["avg_cost"])
    realized = (price - avg_cost) * quantity

    remaining = held - quantity
    if remaining <= 1e-9:
        positions_repo.delete_position(conn, ticker, user_id)
    else:
        positions_repo.upsert_position(
            conn, ticker=ticker, quantity=remaining, avg_cost=avg_cost, user_id=user_id
        )

    proceeds = quantity * price
    new_balance = profile_repo.adjust_cash_balance(conn, proceeds, user_id)
    return new_balance, realized


def _total_portfolio_value(
    conn: sqlite3.Connection, cache: PriceCache, user_id: str
) -> float:
    """Cash + sum(position quantity * current price). Falls back to avg_cost when no price."""
    balance = profile_repo.get_cash_balance(conn, user_id)
    total = balance
    for row in positions_repo.list_positions(conn, user_id):
        price = cache.get_price(row["ticker"])
        if price is None:
            price = float(row["avg_cost"])
        total += float(row["quantity"]) * price
    return round(total, 2)


def total_portfolio_value(
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> float:
    """Compute current total portfolio value (cash + positions)."""
    with transaction(db_path) as conn:
        return _total_portfolio_value(conn, cache, user_id)


def record_value_snapshot(
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> float:
    """Compute total value and record a snapshot row. Returns the value."""
    with transaction(db_path) as conn:
        total = _total_portfolio_value(conn, cache, user_id)
        snapshots_repo.record_snapshot(conn, total_value=total, user_id=user_id)
    return total
