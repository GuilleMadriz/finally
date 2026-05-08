"""Trade execution unit tests."""

from __future__ import annotations

import pytest

from app.db import connect
from app.db.repositories import positions_repo, profile_repo, snapshots_repo, trades_repo
from app.market import PriceCache
from app.services import trading


def test_buy_success_decrements_cash_and_creates_position(db_path, cache: PriceCache):
    result = trading.execute_trade(cache, "AAPL", "buy", 5)

    assert result.ticker == "AAPL"
    assert result.side == "buy"
    assert result.quantity == 5
    assert result.price == 190.0
    assert result.cash_balance == pytest.approx(10000 - 5 * 190.0)
    assert result.realized_pnl == 0.0
    assert result.snapshot_total_value == pytest.approx(10000.0, rel=1e-6)

    conn = connect(db_path)
    try:
        assert profile_repo.get_cash_balance(conn) == pytest.approx(10000 - 5 * 190.0)
        pos = positions_repo.get_position(conn, "AAPL")
        assert pos is not None
        assert pos["quantity"] == 5
        assert pos["avg_cost"] == 190.0
        trades = trades_repo.list_trades(conn)
        assert len(trades) == 1
        snaps = snapshots_repo.list_snapshots(conn)
        assert len(snaps) == 1
    finally:
        conn.close()


def test_buy_insufficient_cash(db_path, cache: PriceCache):
    cache.update("AAPL", 190.0)
    with pytest.raises(trading.InsufficientCash):
        trading.execute_trade(cache, "AAPL", "buy", 100)  # 19000 > 10000

    conn = connect(db_path)
    try:
        # Nothing changed — transaction rolled back
        assert profile_repo.get_cash_balance(conn) == 10000.0
        assert positions_repo.get_position(conn, "AAPL") is None
        assert len(trades_repo.list_trades(conn)) == 0
    finally:
        conn.close()


def test_buy_weighted_average_cost(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 10)  # @ 190
    cache.update("AAPL", 200.0)
    trading.execute_trade(cache, "AAPL", "buy", 10)  # @ 200

    conn = connect(db_path)
    try:
        pos = positions_repo.get_position(conn, "AAPL")
        assert pos["quantity"] == 20
        # (10*190 + 10*200) / 20 == 195
        assert pos["avg_cost"] == pytest.approx(195.0)
    finally:
        conn.close()


def test_sell_success(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 210.0)
    result = trading.execute_trade(cache, "AAPL", "sell", 4)

    assert result.realized_pnl == pytest.approx((210 - 190) * 4)

    conn = connect(db_path)
    try:
        pos = positions_repo.get_position(conn, "AAPL")
        assert pos is not None
        assert pos["quantity"] == 6
        # avg_cost preserved on sells
        assert pos["avg_cost"] == 190.0
        # Cash: 10000 - 1900 (buy) + 4*210 (sell)
        assert profile_repo.get_cash_balance(conn) == pytest.approx(10000 - 1900 + 4 * 210)
    finally:
        conn.close()


def test_sell_full_position_deletes_row(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 5)
    trading.execute_trade(cache, "AAPL", "sell", 5)
    conn = connect(db_path)
    try:
        assert positions_repo.get_position(conn, "AAPL") is None
    finally:
        conn.close()


def test_sell_insufficient_shares_no_position(db_path, cache: PriceCache):
    with pytest.raises(trading.InsufficientShares):
        trading.execute_trade(cache, "AAPL", "sell", 1)


def test_sell_insufficient_shares_partial_position(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 2)
    with pytest.raises(trading.InsufficientShares):
        trading.execute_trade(cache, "AAPL", "sell", 5)
    conn = connect(db_path)
    try:
        pos = positions_repo.get_position(conn, "AAPL")
        assert pos["quantity"] == 2
    finally:
        conn.close()


def test_fractional_shares(db_path, cache: PriceCache):
    result = trading.execute_trade(cache, "AAPL", "buy", 0.5)
    assert result.cash_balance == pytest.approx(10000 - 0.5 * 190.0)
    conn = connect(db_path)
    try:
        pos = positions_repo.get_position(conn, "AAPL")
        assert pos["quantity"] == 0.5
    finally:
        conn.close()


def test_unknown_ticker_rejected(db_path, cache: PriceCache):
    with pytest.raises(trading.UnknownTicker):
        trading.execute_trade(cache, "ZZZZ", "buy", 1)


def test_invalid_side_rejected(db_path, cache: PriceCache):
    with pytest.raises(trading.TradeError):
        trading.execute_trade(cache, "AAPL", "hodl", 1)


def test_zero_quantity_rejected(db_path, cache: PriceCache):
    with pytest.raises(trading.TradeError):
        trading.execute_trade(cache, "AAPL", "buy", 0)


def test_snapshot_recorded_on_each_trade(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 1)
    trading.execute_trade(cache, "AAPL", "buy", 1)
    trading.execute_trade(cache, "AAPL", "sell", 1)
    conn = connect(db_path)
    try:
        snaps = snapshots_repo.list_snapshots(conn)
        assert len(snaps) == 3
    finally:
        conn.close()


def test_total_portfolio_value_uses_live_prices(db_path, cache: PriceCache):
    trading.execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 250.0)
    total = trading.total_portfolio_value(cache)
    # cash 8100 + 10 * 250 = 10600
    assert total == pytest.approx(8100 + 10 * 250)
