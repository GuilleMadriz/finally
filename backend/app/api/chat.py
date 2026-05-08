"""Chat endpoint: portfolio context -> LLM -> auto-execute actions -> persist."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_market_source, get_price_cache
from app.db import connect
from app.db.repositories import chat_repo
from app.llm import (
    ChatResponse,
    PortfolioContext,
    PositionContext,
    WatchlistEntry,
    generate_response,
)
from app.llm.schemas import ChatTurn
from app.market import MarketDataSource, PriceCache
from app.services import portfolio as portfolio_service
from app.services import trading
from app.services import watchlist as watchlist_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

HISTORY_LIMIT = 20


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)


class ExecutedTrade(BaseModel):
    ticker: str
    side: str
    quantity: float
    price: float
    error: str | None = None


class ExecutedWatchlistChange(BaseModel):
    ticker: str
    action: str
    applied: bool
    error: str | None = None


class ChatActions(BaseModel):
    trades: list[ExecutedTrade] = Field(default_factory=list)
    watchlist_changes: list[ExecutedWatchlistChange] = Field(default_factory=list)


class ChatOut(BaseModel):
    message: str
    actions: ChatActions


def _build_portfolio_context(cache: PriceCache) -> PortfolioContext:
    view = portfolio_service.get_portfolio(cache)
    entries = watchlist_service.list_entries(cache)
    return PortfolioContext(
        cash_balance=view.cash_balance,
        total_value=view.total_value,
        positions=[
            PositionContext(
                ticker=p.ticker,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                current_price=p.current_price,
                unrealized_pnl=p.unrealized_pnl,
                pnl_percent=p.unrealized_pnl_percent,
            )
            for p in view.positions
        ],
        watchlist=[
            WatchlistEntry(ticker=e.ticker, price=e.price)
            for e in entries
            if e.price is not None
        ],
    )


def _load_recent_history() -> list[ChatTurn]:
    conn = connect()
    try:
        rows = chat_repo.list_messages(conn, limit=HISTORY_LIMIT)
    finally:
        conn.close()
    return [ChatTurn(role=row["role"], content=row["content"]) for row in rows]


def _execute_trades(cache: PriceCache, llm_response: ChatResponse) -> list[ExecutedTrade]:
    executed: list[ExecutedTrade] = []
    for trade in llm_response.trades:
        try:
            result = trading.execute_trade(
                cache, trade.ticker, trade.side, trade.quantity
            )
            executed.append(
                ExecutedTrade(
                    ticker=result.ticker,
                    side=result.side,
                    quantity=result.quantity,
                    price=result.price,
                )
            )
        except trading.TradeError as exc:
            executed.append(
                ExecutedTrade(
                    ticker=trade.ticker,
                    side=trade.side,
                    quantity=trade.quantity,
                    price=0.0,
                    error=str(exc),
                )
            )
    return executed


async def _apply_watchlist_changes(
    market_source: MarketDataSource,
    cache: PriceCache,
    llm_response: ChatResponse,
) -> list[ExecutedWatchlistChange]:
    applied: list[ExecutedWatchlistChange] = []
    for change in llm_response.watchlist_changes:
        try:
            if change.action == "add":
                ticker, _ = await watchlist_service.add(change.ticker, market_source)
                applied.append(
                    ExecutedWatchlistChange(ticker=ticker, action="add", applied=True)
                )
            else:
                ticker, _ = await watchlist_service.remove(
                    change.ticker, market_source, cache
                )
                applied.append(
                    ExecutedWatchlistChange(ticker=ticker, action="remove", applied=True)
                )
        except watchlist_service.InvalidTicker as exc:
            applied.append(
                ExecutedWatchlistChange(
                    ticker=change.ticker,
                    action=change.action,
                    applied=False,
                    error=str(exc),
                )
            )
    return applied


@router.post("/chat", response_model=ChatOut)
async def post_chat(
    body: ChatIn,
    cache: PriceCache = Depends(get_price_cache),
    market_source: MarketDataSource = Depends(get_market_source),
) -> ChatOut:
    portfolio_ctx = await asyncio.to_thread(_build_portfolio_context, cache)
    history = await asyncio.to_thread(_load_recent_history)

    try:
        llm_response = await generate_response(portfolio_ctx, history, body.message)
    except Exception as exc:  # pydantic.ValidationError, network, etc.
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    trades = await asyncio.to_thread(_execute_trades, cache, llm_response)
    watchlist_changes = await _apply_watchlist_changes(market_source, cache, llm_response)
    actions = ChatActions(trades=trades, watchlist_changes=watchlist_changes)

    def _persist() -> None:
        conn = connect()
        try:
            chat_repo.append_message(conn, role="user", content=body.message)
            chat_repo.append_message(
                conn,
                role="assistant",
                content=llm_response.message,
                actions=actions.model_dump(),
            )
        finally:
            conn.close()

    await asyncio.to_thread(_persist)

    return ChatOut(message=llm_response.message, actions=actions)
