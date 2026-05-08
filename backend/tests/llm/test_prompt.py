"""Tests for prompt assembly."""

from app.llm.prompt import SYSTEM_PROMPT, build_messages
from app.llm.schemas import ChatTurn, PortfolioContext, PositionContext, WatchlistEntry


def _empty_ctx() -> PortfolioContext:
    return PortfolioContext(cash_balance=10000.0, total_value=10000.0)


def _full_ctx() -> PortfolioContext:
    return PortfolioContext(
        cash_balance=5000.0,
        total_value=12345.67,
        positions=[
            PositionContext(
                ticker="AAPL",
                quantity=10,
                avg_cost=180.0,
                current_price=190.5,
                unrealized_pnl=105.0,
                pnl_percent=5.83,
            )
        ],
        watchlist=[WatchlistEntry(ticker="GOOGL", price=175.25)],
    )


class TestBuildMessages:
    def test_first_two_messages_are_system(self):
        msgs = build_messages(_empty_ctx(), [], "hi")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == SYSTEM_PROMPT
        assert msgs[1]["role"] == "system"

    def test_user_message_is_last(self):
        msgs = build_messages(_empty_ctx(), [], "what's my balance?")
        assert msgs[-1] == {"role": "user", "content": "what's my balance?"}

    def test_history_preserved_in_order(self):
        history = [
            ChatTurn(role="user", content="first question"),
            ChatTurn(role="assistant", content="first answer"),
            ChatTurn(role="user", content="follow up"),
            ChatTurn(role="assistant", content="follow up answer"),
        ]
        msgs = build_messages(_empty_ctx(), history, "new question")
        # 2 system + 4 history + 1 new user
        assert len(msgs) == 7
        assert msgs[2]["content"] == "first question"
        assert msgs[5]["content"] == "follow up answer"
        assert msgs[6]["content"] == "new question"

    def test_portfolio_context_includes_balance_and_total(self):
        msgs = build_messages(_full_ctx(), [], "hello")
        ctx_block = msgs[1]["content"]
        assert "$5,000.00" in ctx_block
        assert "$12,345.67" in ctx_block

    def test_portfolio_context_includes_positions_and_watchlist(self):
        msgs = build_messages(_full_ctx(), [], "hello")
        ctx_block = msgs[1]["content"]
        assert "AAPL" in ctx_block
        assert "GOOGL" in ctx_block
        assert "$190.50" in ctx_block
        assert "+5.83%" in ctx_block

    def test_empty_portfolio_renders_placeholders(self):
        msgs = build_messages(_empty_ctx(), [], "hi")
        ctx_block = msgs[1]["content"]
        assert "(none)" in ctx_block
        assert "(empty)" in ctx_block
