"""Chat endpoint tests using LLM_MOCK=true (no network).

Mock LLM trigger contract (see ``app/llm/client.py``):
    - "buy <qty> <TICKER>"   -> trade
    - "sell <qty> <TICKER>"  -> trade
    - "add <TICKER>"         -> watchlist add
    - "remove <TICKER>"      -> watchlist remove
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.db.connection import reset_init_cache
from app.db.repositories import chat_repo, positions_repo, profile_repo, watchlist_repo
from app.main import create_app


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_init_cache()
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_chat_basic_message_persists_pair(app_client: TestClient):
    resp = app_client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"].startswith("Mock:")
    assert body["actions"]["trades"] == []
    assert body["actions"]["watchlist_changes"] == []

    conn = connect()
    try:
        rows = chat_repo.list_messages(conn)
    finally:
        conn.close()
    assert len(rows) == 2
    assert rows[0]["role"] == "user"
    assert rows[1]["role"] == "assistant"


def test_chat_buy_intent_executes_trade(app_client: TestClient):
    resp = app_client.post("/api/chat", json={"message": "buy 1 AAPL"})
    assert resp.status_code == 200
    body = resp.json()
    trades = body["actions"]["trades"]
    assert len(trades) == 1
    trade = trades[0]
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 1.0
    assert trade["error"] is None
    assert trade["price"] > 0

    conn = connect()
    try:
        positions = positions_repo.list_positions(conn)
        assert len(positions) == 1
        assert positions[0]["ticker"] == "AAPL"
        assert positions[0]["quantity"] == 1.0
        assert profile_repo.get_cash_balance(conn) < 10000.0
    finally:
        conn.close()


def test_chat_buy_insufficient_cash_returns_error_inline(app_client: TestClient):
    conn = connect()
    try:
        profile_repo.set_cash_balance(conn, 0.5)
    finally:
        conn.close()

    resp = app_client.post("/api/chat", json={"message": "buy 1 AAPL"})
    assert resp.status_code == 200
    body = resp.json()
    trades = body["actions"]["trades"]
    assert len(trades) == 1
    assert trades[0]["error"] is not None
    assert "insufficient cash" in trades[0]["error"].lower()

    conn = connect()
    try:
        assert positions_repo.list_positions(conn) == []
        # cash unchanged because the rollback inside execute_trade restores it
        assert profile_repo.get_cash_balance(conn) == pytest.approx(0.5)
    finally:
        conn.close()


def test_chat_watchlist_add_applies(app_client: TestClient):
    resp = app_client.post("/api/chat", json={"message": "add PYPL"})
    assert resp.status_code == 200
    body = resp.json()
    changes = body["actions"]["watchlist_changes"]
    assert len(changes) == 1
    assert changes[0]["ticker"] == "PYPL"
    assert changes[0]["action"] == "add"
    assert changes[0]["applied"] is True

    conn = connect()
    try:
        assert watchlist_repo.has_ticker(conn, "PYPL")
    finally:
        conn.close()


def test_chat_watchlist_remove_applies(app_client: TestClient):
    resp = app_client.post("/api/chat", json={"message": "remove AAPL"})
    assert resp.status_code == 200
    body = resp.json()
    changes = body["actions"]["watchlist_changes"]
    assert len(changes) == 1
    assert changes[0]["ticker"] == "AAPL"
    assert changes[0]["action"] == "remove"
    assert changes[0]["applied"] is True

    conn = connect()
    try:
        assert not watchlist_repo.has_ticker(conn, "AAPL")
    finally:
        conn.close()


def test_chat_history_carries_into_context(app_client: TestClient):
    app_client.post("/api/chat", json={"message": "first"})
    app_client.post("/api/chat", json={"message": "second"})
    conn = connect()
    try:
        rows = chat_repo.list_messages(conn)
    finally:
        conn.close()
    assert len(rows) == 4  # two user + two assistant
    assert [r["role"] for r in rows] == ["user", "assistant", "user", "assistant"]


def test_chat_actions_persisted_on_assistant_row(app_client: TestClient):
    app_client.post("/api/chat", json={"message": "buy 1 MSFT"})
    conn = connect()
    try:
        rows = chat_repo.list_messages(conn)
        assistant_row = rows[1]
        actions = chat_repo.parse_actions(assistant_row)
    finally:
        conn.close()
    assert actions is not None
    assert actions["trades"][0]["ticker"] == "MSFT"


def test_chat_empty_message_rejected(app_client: TestClient):
    resp = app_client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 422
