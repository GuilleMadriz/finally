"""Tests for LLM structured-output schemas."""

import pytest
from pydantic import ValidationError

from app.llm.schemas import ChatResponse, TradeAction, WatchlistChange


class TestTradeAction:
    def test_valid_buy(self):
        t = TradeAction(ticker="aapl", side="buy", quantity=10.5)
        assert t.ticker == "AAPL"
        assert t.side == "buy"
        assert t.quantity == 10.5

    def test_valid_sell_with_whitespace(self):
        t = TradeAction(ticker="  msft ", side="sell", quantity=1)
        assert t.ticker == "MSFT"

    def test_invalid_side(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="hold", quantity=1)

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=-5)


class TestWatchlistChange:
    def test_add(self):
        w = WatchlistChange(ticker="pypl", action="add")
        assert w.ticker == "PYPL"
        assert w.action == "add"

    def test_remove(self):
        w = WatchlistChange(ticker="NFLX", action="remove")
        assert w.action == "remove"

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            WatchlistChange(ticker="AAPL", action="watch")


class TestChatResponse:
    def test_minimal_valid(self):
        r = ChatResponse(message="Hello.")
        assert r.message == "Hello."
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_full_payload_from_json(self):
        raw = """{
            "message": "Buying 5 AAPL and adding PYPL.",
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
            "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
        }"""
        r = ChatResponse.model_validate_json(raw)
        assert r.message.startswith("Buying")
        assert len(r.trades) == 1
        assert r.trades[0].ticker == "AAPL"
        assert r.watchlist_changes[0].ticker == "PYPL"

    def test_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatResponse.model_validate_json('{"trades": []}')

    def test_malformed_trade_rejected(self):
        raw = '{"message": "x", "trades": [{"ticker": "AAPL", "side": "BUY", "quantity": 1}]}'
        with pytest.raises(ValidationError):
            ChatResponse.model_validate_json(raw)

    def test_malformed_json_rejected(self):
        with pytest.raises(ValidationError):
            ChatResponse.model_validate_json("not json")
