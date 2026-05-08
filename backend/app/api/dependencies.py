"""Shared FastAPI dependencies.

The :func:`create_app` lifespan stores the ``PriceCache`` and ``MarketDataSource``
on ``app.state``. Route handlers obtain them via these dependencies, which look
them up via ``Request.app.state`` so testing can inject custom values without
changing the route signatures.
"""

from __future__ import annotations

from fastapi import Request

from app.market import MarketDataSource, PriceCache


def get_price_cache(request: Request) -> PriceCache:
    return request.app.state.price_cache


def get_market_source(request: Request) -> MarketDataSource:
    return request.app.state.market_source
