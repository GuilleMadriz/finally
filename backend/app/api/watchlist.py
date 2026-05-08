"""Watchlist REST endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_market_source, get_price_cache
from app.market import MarketDataSource, PriceCache
from app.services import watchlist as watchlist_service

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistEntryOut(BaseModel):
    ticker: str
    price: float | None
    previous_price: float | None
    change: float | None
    change_percent: float | None
    direction: str


class WatchlistOut(BaseModel):
    entries: list[WatchlistEntryOut]


class AddTickerIn(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=8)


class AddTickerOut(BaseModel):
    ticker: str
    added: bool


class RemoveTickerOut(BaseModel):
    ticker: str
    removed: bool


@router.get("", response_model=WatchlistOut)
async def get_watchlist(
    cache: PriceCache = Depends(get_price_cache),
) -> WatchlistOut:
    entries = await asyncio.to_thread(watchlist_service.list_entries, cache)
    return WatchlistOut(
        entries=[
            WatchlistEntryOut(
                ticker=e.ticker,
                price=e.price,
                previous_price=e.previous_price,
                change=e.change,
                change_percent=e.change_percent,
                direction=e.direction,
            )
            for e in entries
        ]
    )


@router.post("", response_model=AddTickerOut, status_code=201)
async def post_watchlist(
    body: AddTickerIn,
    market_source: MarketDataSource = Depends(get_market_source),
) -> AddTickerOut:
    try:
        normalized, added = await watchlist_service.add(body.ticker, market_source)
    except watchlist_service.InvalidTicker as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AddTickerOut(ticker=normalized, added=added)


@router.delete("/{ticker}", response_model=RemoveTickerOut)
async def delete_watchlist(
    ticker: str,
    market_source: MarketDataSource = Depends(get_market_source),
    cache: PriceCache = Depends(get_price_cache),
) -> RemoveTickerOut:
    try:
        normalized, removed = await watchlist_service.remove(ticker, market_source, cache)
    except watchlist_service.InvalidTicker as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RemoveTickerOut(ticker=normalized, removed=removed)
