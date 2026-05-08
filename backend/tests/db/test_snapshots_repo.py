"""Tests for snapshots_repo."""

from __future__ import annotations

import sqlite3

from app.db.repositories import snapshots_repo


class TestSnapshotsRepo:
    def test_record_snapshot(self, conn: sqlite3.Connection):
        snapshots_repo.record_snapshot(conn, 10000.0)
        rows = snapshots_repo.list_snapshots(conn)
        assert len(rows) == 1
        assert rows[0]["total_value"] == 10000.0

    def test_list_snapshots_oldest_first(self, conn: sqlite3.Connection):
        snapshots_repo.record_snapshot(
            conn, 10000.0, recorded_at="2026-01-01T00:00:00+00:00"
        )
        snapshots_repo.record_snapshot(
            conn, 10100.0, recorded_at="2026-01-02T00:00:00+00:00"
        )
        snapshots_repo.record_snapshot(
            conn, 10200.0, recorded_at="2026-01-03T00:00:00+00:00"
        )
        rows = snapshots_repo.list_snapshots(conn)
        values = [r["total_value"] for r in rows]
        assert values == [10000.0, 10100.0, 10200.0]

    def test_list_snapshots_limit_returns_recent_oldest_first(self, conn: sqlite3.Connection):
        for i in range(5):
            snapshots_repo.record_snapshot(
                conn,
                10000.0 + i * 100,
                recorded_at=f"2026-01-0{i + 1}T00:00:00+00:00",
            )
        rows = snapshots_repo.list_snapshots(conn, limit=2)
        assert len(rows) == 2
        # Most recent two, ordered oldest first.
        assert rows[0]["total_value"] == 10300.0
        assert rows[1]["total_value"] == 10400.0
