"""SQLite connection helper with lazy initialization and seeding."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Iterator

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0
DEFAULT_WATCHLIST = (
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_init_lock = Lock()
_initialized_paths: set[Path] = set()


def get_db_path() -> Path:
    """Resolve the SQLite file location.

    Honors FINALLY_DB_PATH env var; otherwise defaults to ``db/finally.db``
    relative to the project root (the parent of ``backend/``).
    """
    env_path = os.environ.get("FINALLY_DB_PATH")
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "db" / "finally.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection, ensuring the schema is initialized.

    Returns a connection with row factory set to ``sqlite3.Row`` and foreign
    keys enabled.
    """
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    init_db(path)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Lazily create tables and seed defaults if not already initialized.

    Safe to call repeatedly: schema uses ``CREATE TABLE IF NOT EXISTS`` and
    seeding checks for existing rows. The ``_initialized_paths`` cache avoids
    repeating the work on every connection.
    """
    path = db_path or get_db_path()
    with _init_lock:
        if path in _initialized_paths and path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        conn = sqlite3.connect(path, isolation_level=None)
        try:
            conn.executescript(schema_sql)
            _seed(conn)
        finally:
            conn.close()
        _initialized_paths.add(path)


def _seed(conn: sqlite3.Connection) -> None:
    """Insert default profile and watchlist rows if missing."""
    now = utc_now_iso()
    conn.execute(
        """
        INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at)
        VALUES (?, ?, ?)
        """,
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )
    for ticker in DEFAULT_WATCHLIST:
        conn.execute(
            """
            INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (new_id(), DEFAULT_USER_ID, ticker, now),
        )


@contextmanager
def transaction(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection wrapped in a transaction.

    Commits on clean exit, rolls back on exception, and closes the connection.
    """
    conn = connect(db_path)
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def new_id() -> str:
    """Generate a hex UUID for primary keys."""
    return uuid.uuid4().hex


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def reset_init_cache() -> None:
    """Clear the in-process init cache. Intended for tests."""
    with _init_lock:
        _initialized_paths.clear()
