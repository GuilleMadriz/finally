"""End-to-end smoke tests for the wired FastAPI app (with lifespan)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.connection import reset_init_cache
from app.main import create_app


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """TestClient with full lifespan: init_db, simulator started, snapshot loop running."""
    reset_init_cache()
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_app_boots_health_endpoint(app_client: TestClient):
    resp = app_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_portfolio_endpoint_through_lifespan(app_client: TestClient):
    resp = app_client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cash_balance"] == 10000.0
    assert body["positions"] == []


def test_watchlist_endpoint_through_lifespan(app_client: TestClient):
    resp = app_client.get("/api/watchlist")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    tickers = {e["ticker"] for e in entries}
    assert tickers == {
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
        "NVDA", "META", "JPM", "V", "NFLX",
    }


def test_stream_prices_route_binds_request_correctly():
    """Regression: ``from __future__ import annotations`` + a function-local
    ``Request`` import caused FastAPI to treat the ``request`` parameter as a
    query parameter, producing 422 on every call.

    We can't hit the live route from TestClient (the SSE generator never
    terminates, so any in-process consumer hangs), but we can introspect the
    route's dependency tree to confirm ``request`` is wired as the actual
    Starlette Request object — not as a missing query field.
    """
    from starlette.requests import Request as StarletteRequest

    from app.main import create_app

    app = create_app()
    route = next(r for r in app.routes if getattr(r, "path", None) == "/api/stream/prices")
    dep = route.dependant  # type: ignore[attr-defined]
    # If the bug returned, ``request`` would appear in dep.query_params here.
    query_param_names = {p.name for p in dep.query_params}
    assert "request" not in query_param_names
    # And ``request`` must be wired as the Starlette Request kwarg.
    assert dep.request_param_name == "request" or any(
        p.type_ is StarletteRequest for p in dep.params or []
    )
