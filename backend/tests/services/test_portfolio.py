"""Portfolio view tests."""

from __future__ import annotations

import pytest

from app.market import PriceCache
from app.services import portfolio, trading


def test_empty_portfolio_no_positions(db_path, cache: PriceCache):
    view = portfolio.get_portfolio(cache)
    assert view.cash_balance == 10000.0
    assert view.positions == []
    assert view.total_value == 10000.0
    assert view.total_unrealized_pnl == 0.0


def test_portfolio_after_buy_unrealized_pnl(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 10)  # @ 190
    cache.update("AAPL", 200.0)

    view = portfolio.get_portfolio(cache)
    assert view.cash_balance == pytest.approx(10000 - 1900)
    assert len(view.positions) == 1
    pos = view.positions[0]
    assert pos.ticker == "AAPL"
    assert pos.quantity == 10
    assert pos.avg_cost == 190.0
    assert pos.current_price == 200.0
    assert pos.market_value == 2000.0
    assert pos.unrealized_pnl == pytest.approx(100.0)
    assert pos.unrealized_pnl_percent == pytest.approx((10 / 190) * 100, abs=0.01)
    assert view.total_value == pytest.approx(8100 + 2000)
    assert view.total_unrealized_pnl == pytest.approx(100.0)


def test_portfolio_history_returns_snapshots_oldest_first(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 1)
    trading.execute_trade(cache, "AAPL", "buy", 1)
    trading.execute_trade(cache, "AAPL", "sell", 1)
    points = portfolio.get_history()
    assert len(points) == 3
    # ordered ascending recorded_at
    times = [p.recorded_at for p in points]
    assert times == sorted(times)


def test_portfolio_falls_back_to_avg_cost_when_no_price(db_path):
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    trading.execute_trade(cache, "AAPL", "buy", 5)
    cache.remove("AAPL")
    view = portfolio.get_portfolio(cache)
    assert view.positions[0].current_price == 100.0
    assert view.positions[0].unrealized_pnl == 0.0
