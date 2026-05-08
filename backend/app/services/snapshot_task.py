"""Periodic portfolio_snapshots writer.

The chat endpoint and trade endpoint each write a snapshot row at the moment
of an action. This background task adds a coarse-grained sample every 30s so
the P&L chart still gets points during quiet periods.
"""

from __future__ import annotations

import asyncio
import logging

from app.market import PriceCache
from app.services import trading

logger = logging.getLogger(__name__)


async def run_snapshot_loop(cache: PriceCache, interval: float = 30.0) -> None:
    """Forever: every ``interval`` seconds, write a portfolio snapshot row.

    Cancelling the task is the supported stop signal.
    """
    while True:
        try:
            await asyncio.sleep(interval)
            await asyncio.to_thread(trading.record_value_snapshot, cache)
        except asyncio.CancelledError:
            logger.info("snapshot loop cancelled")
            raise
        except Exception:
            logger.exception("snapshot write failed")
