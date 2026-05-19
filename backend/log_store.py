"""SQLite-backed operational event log store."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

import storage

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
MAX_RETAINED_ROWS = 5000


def _json_default(value: Any) -> str:
    return str(value)


def _safe_metadata(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return "{}"
    return json.dumps(metadata, default=_json_default, sort_keys=True)


def record_event(
    *,
    level: str = "info",
    category: str,
    event: str,
    status: str,
    message: str = "",
    recording_id: str | None = None,
    job_id: str | None = None,
    dispatch_id: str | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Persist an operational event.

    This function intentionally does not catch errors. Callers that run on
    product-critical paths should use `observability.log_event`, which wraps
    this in a best-effort guard.
    """
    conn = storage._get_conn()
    event_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO logs (
            id, level, category, event, status, message, recording_id,
            job_id, dispatch_id, duration_ms, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            level.lower(),
            category,
            event,
            status,
            message,
            recording_id,
            job_id,
            dispatch_id,
            duration_ms,
            _safe_metadata(metadata),
        ),
    )
    conn.execute(
        """
        DELETE FROM logs
        WHERE rowid NOT IN (
            SELECT rowid FROM logs
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
        )
        """,
        (MAX_RETAINED_ROWS,),
    )
    conn.commit()
    return get_event(event_id)


def get_event(event_id: str) -> dict[str, Any] | None:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM logs WHERE id = ?", (event_id,)).fetchone()
    conn.row_factory = None
    return _row_to_dict(row) if row else None


def list_events(
    *,
    limit: int = DEFAULT_LIMIT,
    category: str | None = None,
    status: str | None = None,
    recording_id: str | None = None,
    job_id: str | None = None,
    dispatch_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return newest operational events with optional exact-match filters."""
    safe_limit = max(1, min(limit, MAX_LIMIT))
    where: list[str] = []
    params: list[Any] = []

    for column, value in (
        ("category", category),
        ("status", status),
        ("recording_id", recording_id),
        ("job_id", job_id),
        ("dispatch_id", dispatch_id),
    ):
        if value:
            where.append(f"{column} = ?")
            params.append(value)

    sql = "SELECT * FROM logs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
    params.append(safe_limit)

    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.row_factory = None
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    try:
        data["metadata"] = json.loads(data.get("metadata") or "{}")
    except json.JSONDecodeError:
        data["metadata"] = {}
    return data
