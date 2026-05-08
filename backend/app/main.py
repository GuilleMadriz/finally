"""FastAPI app factory + lifespan wiring.

Run locally with:
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

Lifespan responsibilities:
    * Initialize SQLite (lazy seed via ``init_db``).
    * Build a :class:`PriceCache` and a :class:`MarketDataSource` (simulator
      or Massive, decided by env), then start the source on the current
      watchlist tickers from the DB.
    * Mount the SSE router (it needs the cache by reference, so it's added
      to the app at startup, not at module-import time).
    * Spawn the periodic snapshot task.
    * On shutdown: cancel snapshot task, stop the market source.

Routes obtain the shared cache/source via ``request.app.state`` (see
``app.api.dependencies``); routers themselves are import-time, no hard refs.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api.dependencies import get_market_source, get_price_cache  # noqa: F401  (re-export)
from app.api.health import router as health_router
from app.api.portfolio import router as portfolio_router
from app.api.watchlist import router as watchlist_router
from app.db import connect, init_db
from app.db.repositories import watchlist_repo
from app.market import PriceCache, create_market_data_source
from app.market.stream import _generate_events
from app.services.snapshot_task import run_snapshot_loop

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _load_initial_tickers() -> list[str]:
    conn = connect()
    try:
        return watchlist_repo.list_tickers(conn)
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()

    cache = PriceCache()
    market_source = create_market_data_source(cache)
    initial_tickers = _load_initial_tickers()
    await market_source.start(initial_tickers)
    logger.info("market source started with %d tickers", len(initial_tickers))

    snapshot_task = asyncio.create_task(run_snapshot_loop(cache), name="snapshot-loop")

    app.state.price_cache = cache
    app.state.market_source = market_source
    app.state.snapshot_task = snapshot_task

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await market_source.stop()


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="FinAlly", lifespan=lifespan)

    # API routers — registered before any catch-all static route.
    app.include_router(health_router)
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)

    # SSE stream router. Constructed eagerly with a placeholder cache; at
    # import time we have no cache yet, so we wire the route via a tiny
    # closure that defers cache lookup to request time.
    _mount_stream_route(app)

    # Chat router is included if available (LLM module is present).
    try:
        from app.api.chat import router as chat_router

        app.include_router(chat_router)
    except ImportError:
        logger.info("chat router not yet available")

    _mount_static(app)
    return app


def _mount_stream_route(app: FastAPI) -> None:
    """Wire SSE under /api/stream/prices using the lifespan-built cache.

    The cache only exists at request time (built in lifespan), so this proxy
    route reads it from ``app.state``. The Request/StreamingResponse imports
    must be module-level: ``from __future__ import annotations`` defers the
    annotation strings, and FastAPI resolves them with module globals.
    """

    @app.get("/api/stream/prices", tags=["streaming"])
    async def stream_prices(request: Request) -> StreamingResponse:
        cache: PriceCache = request.app.state.price_cache
        return StreamingResponse(
            _generate_events(cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


def _mount_static(app: FastAPI) -> None:
    """Serve the Next.js static export at the root with SPA fallback.

    All ``/api/*`` routes are registered above this, so they take precedence.
    """
    if not STATIC_DIR.is_dir():
        logger.info("static dir not present at %s; skipping static mount", STATIC_DIR)
        return

    app.mount("/_next", StaticFiles(directory=STATIC_DIR / "_next"), name="next-assets")
    app.mount(
        "/static-assets",
        StaticFiles(directory=STATIC_DIR),
        name="static-assets",
    )

    index_file = STATIC_DIR / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


app = create_app()
