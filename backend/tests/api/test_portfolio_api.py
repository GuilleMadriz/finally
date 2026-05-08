"""Portfolio HTTP route tests."""

from __future__ import annotations


def test_get_portfolio_default(client):
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash_balance"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0


def test_buy_and_get_portfolio_returns_position(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 190.0
    assert body["cash_balance"] == 10000 - 5 * 190.0

    portfolio = client.get("/api/portfolio").json()
    assert len(portfolio["positions"]) == 1
    pos = portfolio["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 5
    assert pos["avg_cost"] == 190.0


def test_buy_insufficient_cash_returns_400(client):
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 1000},
    )
    assert resp.status_code == 400
    assert "insufficient cash" in resp.json()["detail"]


def test_sell_more_than_held_returns_400(client):
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 1}
    )
    assert resp.status_code == 400


def test_unknown_ticker_returns_404(client):
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "ZZZZ", "side": "buy", "quantity": 1},
    )
    assert resp.status_code == 404


def test_invalid_side_rejected_by_pydantic(client):
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "side": "hodl", "quantity": 1}
    )
    assert resp.status_code == 422


def test_zero_quantity_rejected_by_pydantic(client):
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 0}
    )
    assert resp.status_code == 422


def test_history_endpoint_returns_points(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1})
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1})
    resp = client.get("/api/portfolio/history")
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 2
    assert all("recorded_at" in p and "total_value" in p for p in points)
