"""Watchlist HTTP route tests."""

from __future__ import annotations


def test_get_watchlist_returns_seeded_entries(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    tickers = {e["ticker"] for e in entries}
    assert tickers == {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}
    assert all(e["price"] is not None for e in entries)


def test_post_watchlist_adds_ticker_and_calls_source(client, market_source):
    resp = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 201
    body = resp.json()
    assert body == {"ticker": "PYPL", "added": True}
    assert "PYPL" in market_source.added

    entries = client.get("/api/watchlist").json()["entries"]
    tickers = [e["ticker"] for e in entries]
    assert "PYPL" in tickers


def test_post_watchlist_existing_ticker_idempotent(client, market_source):
    resp = client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 201
    assert resp.json() == {"ticker": "AAPL", "added": False}
    assert "AAPL" in market_source.added


def test_post_watchlist_invalid_ticker_returns_400(client):
    resp = client.post("/api/watchlist", json={"ticker": "ab-c"})
    assert resp.status_code == 400


def test_delete_watchlist_removes_ticker_and_calls_source(client, market_source):
    resp = client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    assert resp.json() == {"ticker": "AAPL", "removed": True}
    assert "AAPL" in market_source.removed

    entries = client.get("/api/watchlist").json()["entries"]
    tickers = [e["ticker"] for e in entries]
    assert "AAPL" not in tickers


def test_delete_missing_ticker_returns_false(client, market_source):
    resp = client.delete("/api/watchlist/NOPE")
    assert resp.status_code == 200
    assert resp.json() == {"ticker": "NOPE", "removed": False}


def test_delete_invalid_ticker_format_returns_400(client):
    resp = client.delete("/api/watchlist/ab-c")
    assert resp.status_code == 400
