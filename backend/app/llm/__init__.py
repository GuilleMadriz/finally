"""LLM chat integration: structured outputs via OpenRouter (Cerebras)."""

from .client import generate_response
from .schemas import (
    ChatResponse,
    PortfolioContext,
    PositionContext,
    TradeAction,
    WatchlistChange,
    WatchlistEntry,
)

__all__ = [
    "ChatResponse",
    "PortfolioContext",
    "PositionContext",
    "TradeAction",
    "WatchlistChange",
    "WatchlistEntry",
    "generate_response",
]
