"""Tests for the LLM client (mock-mode determinism, no live API calls)."""

import pytest

from app.llm.client import generate_response
from app.llm.schemas import (
    ChatResponse,
    PortfolioContext,
    PositionContext,
    WatchlistEntry,
)


@pytest.fixture(autouse=True)
def enable_mock(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


def _ctx_with_watchlist() -> PortfolioContext:
    return PortfolioContext(
        cash_balance=10000.0,
        total_value=10000.0,
        watchlist=[WatchlistEntry(ticker="TSLA", price=250.0)],
    )


def _ctx_with_position() -> PortfolioContext:
    return PortfolioContext(
        cash_balance=8000.0,
        total_value=10000.0,
        positions=[
            PositionContext(
                ticker="NVDA",
                quantity=2,
                avg_cost=900,
                current_price=1000,
                unrealized_pnl=200,
                pnl_percent=11.11,
            )
        ],
    )


class TestMockResponses:
    async def test_mock_returns_chat_response_with_no_action_for_plain_text(self):
        resp = await generate_response(_ctx_with_watchlist(), [], "hello there")
        assert isinstance(resp, ChatResponse)
        assert resp.message.startswith("Mock:")
        assert resp.trades == []
        assert resp.watchlist_changes == []

    async def test_mock_buy_trigger_emits_trade(self):
        resp = await generate_response(_ctx_with_watchlist(), [], "buy 1 AAPL")
        assert len(resp.trades) == 1
        t = resp.trades[0]
        assert t.side == "buy"
        assert t.ticker == "AAPL"
        assert t.quantity == 1
        assert resp.watchlist_changes == []

    async def test_mock_buy_trigger_is_case_insensitive(self):
        resp = await generate_response(_ctx_with_watchlist(), [], "Buy 2.5 nvda please")
        assert len(resp.trades) == 1
        assert resp.trades[0].side == "buy"
        assert resp.trades[0].ticker == "NVDA"
        assert resp.trades[0].quantity == 2.5

    async def test_mock_sell_trigger_emits_trade(self):
        resp = await generate_response(_ctx_with_position(), [], "sell 3 NVDA")
        assert len(resp.trades) == 1
        assert resp.trades[0].side == "sell"
        assert resp.trades[0].ticker == "NVDA"
        assert resp.trades[0].quantity == 3

    async def test_mock_add_trigger_emits_watchlist_change(self):
        resp = await generate_response(_ctx_with_watchlist(), [], "add PYPL")
        assert resp.trades == []
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "PYPL"
        assert resp.watchlist_changes[0].action == "add"

    async def test_mock_remove_trigger_emits_watchlist_change(self):
        resp = await generate_response(_ctx_with_watchlist(), [], "remove NFLX from list")
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "NFLX"
        assert resp.watchlist_changes[0].action == "remove"

    async def test_mock_word_buy_alone_does_not_trigger_trade(self):
        """Bare 'buy' without 'qty TICKER' must not fire a trade — strict pattern."""
        resp = await generate_response(_ctx_with_watchlist(), [], "should i buy something?")
        assert resp.trades == []

    async def test_mock_is_deterministic(self):
        ctx = _ctx_with_watchlist()
        r1 = await generate_response(ctx, [], "buy 1 AAPL")
        r2 = await generate_response(ctx, [], "buy 1 AAPL")
        assert r1.model_dump() == r2.model_dump()

    async def test_mock_echo_includes_user_message(self):
        resp = await generate_response(_ctx_with_watchlist(), [], "Pineapple")
        assert "Pineapple" in resp.message

    async def test_mock_message_always_starts_with_prefix(self):
        cases = ["hello", "buy 1 AAPL", "sell 2 NVDA", "add PYPL", "remove TSLA"]
        for msg in cases:
            resp = await generate_response(_ctx_with_watchlist(), [], msg)
            assert resp.message.startswith("Mock:"), f"failed for input: {msg!r}"


class TestMockDisabled:
    async def test_no_network_call_when_mock_disabled_and_no_key(self, monkeypatch):
        """With LLM_MOCK unset, calling out should hit the patched completion."""
        monkeypatch.delenv("LLM_MOCK", raising=False)

        called = {"n": 0}

        def fake_completion(**kwargs):
            called["n"] += 1
            raise RuntimeError("blocked: no network in tests")

        import app.llm.client as client_mod

        monkeypatch.setattr(client_mod, "completion", fake_completion)

        with pytest.raises(RuntimeError, match="blocked"):
            await generate_response(_ctx_with_watchlist(), [], "hi")
        assert called["n"] == 1
