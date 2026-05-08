"""Pydantic schemas for LLM chat structured outputs and supporting context."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradeAction(BaseModel):
    """A single trade the LLM wants to execute on behalf of the user."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class WatchlistChange(BaseModel):
    """A single watchlist modification requested by the LLM."""

    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class ChatResponse(BaseModel):
    """Structured response returned by the LLM for every chat turn."""

    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)


class PositionContext(BaseModel):
    """Lightweight view of a single position for the LLM prompt."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    pnl_percent: float


class WatchlistEntry(BaseModel):
    """Lightweight view of a watchlist ticker for the LLM prompt."""

    ticker: str
    price: float


class PortfolioContext(BaseModel):
    """Snapshot of the user's portfolio passed into each LLM call."""

    cash_balance: float
    total_value: float
    positions: list[PositionContext] = Field(default_factory=list)
    watchlist: list[WatchlistEntry] = Field(default_factory=list)


class ChatTurn(BaseModel):
    """A prior chat message used to build conversation history."""

    role: Literal["user", "assistant"]
    content: str
