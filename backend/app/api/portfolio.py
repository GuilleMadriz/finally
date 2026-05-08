"""Portfolio REST endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_price_cache
from app.market import PriceCache
from app.services import portfolio as portfolio_service
from app.services import trading

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class PositionOut(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


class PortfolioOut(BaseModel):
    cash_balance: float
    total_value: float
    total_unrealized_pnl: float
    positions: list[PositionOut]


class TradeIn(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=8)
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)


class TradeOut(BaseModel):
    ticker: str
    side: str
    quantity: float
    price: float
    cash_balance: float
    realized_pnl: float
    snapshot_total_value: float


class HistoryPoint(BaseModel):
    recorded_at: str
    total_value: float


class HistoryOut(BaseModel):
    points: list[HistoryPoint]


@router.get("", response_model=PortfolioOut)
async def get_portfolio(
    cache: PriceCache = Depends(get_price_cache),
) -> PortfolioOut:
    view = await asyncio.to_thread(portfolio_service.get_portfolio, cache)
    return PortfolioOut(
        cash_balance=view.cash_balance,
        total_value=view.total_value,
        total_unrealized_pnl=view.total_unrealized_pnl,
        positions=[
            PositionOut(
                ticker=p.ticker,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                current_price=p.current_price,
                market_value=p.market_value,
                unrealized_pnl=p.unrealized_pnl,
                unrealized_pnl_percent=p.unrealized_pnl_percent,
            )
            for p in view.positions
        ],
    )


@router.post("/trade", response_model=TradeOut)
async def post_trade(
    body: TradeIn,
    cache: PriceCache = Depends(get_price_cache),
) -> TradeOut:
    try:
        result = await asyncio.to_thread(
            trading.execute_trade,
            cache,
            body.ticker,
            body.side,
            body.quantity,
        )
    except trading.UnknownTicker as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except trading.TradeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TradeOut(
        ticker=result.ticker,
        side=result.side,
        quantity=result.quantity,
        price=result.price,
        cash_balance=result.cash_balance,
        realized_pnl=result.realized_pnl,
        snapshot_total_value=result.snapshot_total_value,
    )


@router.get("/history", response_model=HistoryOut)
async def get_history() -> HistoryOut:
    points = await asyncio.to_thread(portfolio_service.get_history)
    return HistoryOut(
        points=[HistoryPoint(recorded_at=p.recorded_at, total_value=p.total_value) for p in points]
    )
