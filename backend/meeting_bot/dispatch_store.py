"""SQLite-backed store for in-flight meeting-bot dispatches.

Piggy-backs on the connection opened by `storage.init_db()` so a single
allure.db holds both jobs/attachments and the dispatches table.
"""

import sqlite3
from typing import Any, Optional

import storage

# Lifecycle of a dispatch row:
#   dispatched     -> bot was told to join; no audio yet
#   recording      -> watcher saw a file appear (size may still be growing)
#   stop_requested -> user asked the bot to leave; waiting for finalize
#   forwarding     -> file stable; POSTing to the frontend
#   ingested       -> frontend accepted the upload; pipeline owns it now
#   failed         -> any terminal error (bot timeout, forward failure, etc.)
VALID_STATUSES = {
    "dispatched",
    "recording",
    "stop_requested",
    "forwarding",
    "ingested",
    "failed",
}

# Platforms the bot supports.
VALID_PLATFORMS = {"google", "microsoft", "zoom"}


def init() -> None:
    """Create the dispatches table if it does not already exist."""
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatches (
            recording_id TEXT PRIMARY KEY,
            meeting_url TEXT NOT NULL,
            platform TEXT NOT NULL,
            project_id TEXT,
            title TEXT,
            status TEXT NOT NULL DEFAULT 'dispatched',
            audio_path TEXT,
            dispatched_at TEXT NOT NULL DEFAULT (datetime('now')),
            finalized_at TEXT,
            error TEXT
        )
        """
    )
    conn.commit()


def create(
    recording_id: str,
    meeting_url: str,
    platform: str,
    project_id: Optional[str] = None,
    title: Optional[str] = None,
) -> dict[str, Any]:
    """Insert a new dispatch row in status='dispatched'."""
    if platform not in VALID_PLATFORMS:
        raise ValueError(f"Unknown platform: {platform!r}")
    conn = storage._get_conn()
    conn.execute(
        """
        INSERT INTO dispatches (recording_id, meeting_url, platform, project_id, title)
        VALUES (?, ?, ?, ?, ?)
        """,
        (recording_id, meeting_url, platform, project_id, title),
    )
    conn.commit()
    return get(recording_id)  # type: ignore[return-value]


def get(recording_id: str) -> Optional[dict[str, Any]]:
    """Return a single dispatch row as a dict, or None."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM dispatches WHERE recording_id = ?", (recording_id,)
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def update(recording_id: str, **fields: Any) -> dict[str, Any]:
    """Update one or more columns. Raises KeyError if the row does not exist."""
    if not fields:
        existing = get(recording_id)
        if existing is None:
            raise KeyError(f"Dispatch {recording_id} not found")
        return existing

    if "status" in fields and fields["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {fields['status']!r}")

    conn = storage._get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [recording_id]
    cursor = conn.execute(
        f"UPDATE dispatches SET {sets} WHERE recording_id = ?", values
    )
    if cursor.rowcount == 0:
        raise KeyError(f"Dispatch {recording_id} not found")
    conn.commit()
    return get(recording_id)  # type: ignore[return-value]


def list_pending() -> list[dict[str, Any]]:
    """Return dispatches still waiting on a recording or upload, oldest first."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM dispatches
        WHERE status IN ('dispatched', 'recording', 'stop_requested', 'forwarding')
        ORDER BY dispatched_at ASC
        """
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def delete(recording_id: str) -> bool:
    """Remove a dispatch row. Returns True if a row was deleted."""
    conn = storage._get_conn()
    cursor = conn.execute(
        "DELETE FROM dispatches WHERE recording_id = ?", (recording_id,)
    )
    conn.commit()
    return cursor.rowcount > 0
