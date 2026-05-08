"""Portfolio read-side views: positions enriched with live prices + P&L."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db import DEFAULT_USER_ID, connect
from app.db.repositories import positions_repo, profile_repo, snapshots_repo
from app.market import PriceCache


@dataclass(frozen=True, slots=True)
class PositionView:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


@dataclass(frozen=True, slots=True)
class PortfolioView:
    cash_balance: float
    positions: list[PositionView]
    total_value: float
    total_unrealized_pnl: float


def get_portfolio(
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
    db_path: Path | None = None,
) -> PortfolioView:
    """Snapshot the user's cash + positions, enriched with live prices and P&L.

    When a ticker has no price in the cache, falls back to its avg_cost so the
    portfolio always values cleanly.
    """
    conn = connect(db_path)
    try:
        cash = profile_repo.get_cash_balance(conn, user_id)
        rows = positions_repo.list_positions(conn, user_id)
    finally:
        conn.close()

    positions: list[PositionView] = []
    total_unrealized = 0.0
    for row in rows:
        ticker = row["ticker"]
        qty = float(row["quantity"])
        avg = float(row["avg_cost"])
        price = cache.get_price(ticker)
        if price is None:
            price = avg
        market_value = qty * price
        cost_basis = qty * avg
        unrealized = market_value - cost_basis
        unrealized_pct = (unrealized / cost_basis * 100) if cost_basis else 0.0
        total_unrealized += unrealized
        positions.append(
            PositionView(
                ticker=ticker,
                quantity=qty,
                avg_cost=round(avg, 4),
                current_price=round(price, 2),
                market_value=round(market_value, 2),
                unrealized_pnl=round(unrealized, 2),
                unrealized_pnl_percent=round(unrealized_pct, 2),
            )
        )

    total_value = round(cash + sum(p.market_value for p in positions), 2)
    return PortfolioView(
        cash_balance=round(cash, 2),
        positions=positions,
        total_value=total_value,
        total_unrealized_pnl=round(total_unrealized, 2),
    )


@dataclass(frozen=True, slots=True)
class SnapshotPoint:
    recorded_at: str
    total_value: float


def get_history(
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
    db_path: Path | None = None,
) -> list[SnapshotPoint]:
    """Return portfolio_snapshots ordered oldest-first for the P&L chart."""
    conn = connect(db_path)
    try:
        rows = snapshots_repo.list_snapshots(conn, user_id=user_id, limit=limit)
    finally:
        conn.close()
    return [
        SnapshotPoint(recorded_at=row["recorded_at"], total_value=float(row["total_value"]))
        for row in rows
    ]
