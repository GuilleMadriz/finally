"""LLM call site: LiteLLM via OpenRouter with Cerebras as the inference provider."""

from __future__ import annotations

import asyncio
import os
import re

from litellm import completion

from .prompt import build_messages
from .schemas import ChatResponse, ChatTurn, PortfolioContext

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

# Mock-mode trigger patterns. Deterministic and E2E-test-friendly.
# Examples that match: "buy 1 AAPL", "sell 2.5 NVDA", "add PYPL", "remove TSLA"
_TRADE_RE = re.compile(
    r"\b(?P<side>buy|sell)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<ticker>[A-Z]{1,6})\b",
    re.IGNORECASE,
)
_WATCH_RE = re.compile(
    r"\b(?P<action>add|remove)\s+(?P<ticker>[A-Z]{1,6})\b",
    re.IGNORECASE,
)


def _mock_response(user_message: str, portfolio_ctx: PortfolioContext) -> ChatResponse:
    """Deterministic canned response used when LLM_MOCK=true (E2E tests, dev).

    Triggers (case-insensitive):
    - "buy <qty> <TICKER>"     -> trades=[{ticker, side: "buy",  quantity: qty}]
    - "sell <qty> <TICKER>"    -> trades=[{ticker, side: "sell", quantity: qty}]
    - "add <TICKER>"           -> watchlist_changes=[{ticker, action: "add"}]
    - "remove <TICKER>"        -> watchlist_changes=[{ticker, action: "remove"}]
    - otherwise                -> echo only, no actions

    The `message` field always begins with the literal prefix "Mock:" so tests
    can assert on it cheaply. `portfolio_ctx` is unused — triggers are derived
    purely from `user_message` so the contract is fully deterministic.
    """
    del portfolio_ctx  # contract: triggers come only from user_message

    trade_match = _TRADE_RE.search(user_message)
    if trade_match:
        side = trade_match["side"].lower()
        qty = float(trade_match["qty"])
        ticker = trade_match["ticker"].upper()
        return ChatResponse(
            message=f"Mock: {side} {qty:g} {ticker}.",
            trades=[{"ticker": ticker, "side": side, "quantity": qty}],
        )

    watch_match = _WATCH_RE.search(user_message)
    if watch_match:
        action = watch_match["action"].lower()
        ticker = watch_match["ticker"].upper()
        return ChatResponse(
            message=f"Mock: {action} {ticker} watchlist.",
            watchlist_changes=[{"ticker": ticker, "action": action}],
        )

    return ChatResponse(message=f"Mock: {user_message}")


def _is_mock_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


async def generate_response(
    portfolio_ctx: PortfolioContext,
    history: list[ChatTurn],
    user_message: str,
) -> ChatResponse:
    """Generate a structured chat response.

    Returns a `ChatResponse` parsed from the LLM's JSON output. Honors
    `LLM_MOCK=true` by returning a deterministic canned response (no network).

    Raises `pydantic.ValidationError` if the LLM returns malformed JSON; the
    chat endpoint is responsible for user-facing error wrapping.
    """
    if _is_mock_enabled():
        return _mock_response(user_message, portfolio_ctx)

    messages = build_messages(portfolio_ctx, history, user_message)

    response = await asyncio.to_thread(
        completion,
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )
    raw = response.choices[0].message.content
    return ChatResponse.model_validate_json(raw)
