"""Database subsystem: SQLite schema, lazy init, and repository helpers."""

from .connection import DEFAULT_USER_ID, connect, get_db_path, init_db, transaction

__all__ = ["DEFAULT_USER_ID", "connect", "get_db_path", "init_db", "transaction"]
