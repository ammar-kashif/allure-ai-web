"""SQLite-backed job state store."""

import json
import os
import sqlite3
from typing import Any

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "allure.db")

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        raise RuntimeError("Storage not initialized. Call init_db() first.")
    return _conn


def init_db(db_path: str | None = None) -> None:
    """Initialize the SQLite database and create tables if needed."""
    global _conn
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            error TEXT,
            extraction_status TEXT NOT NULL DEFAULT 'none',
            extraction_error TEXT,
            outcomes TEXT NOT NULL DEFAULT '[]',
            chart_status TEXT NOT NULL DEFAULT 'none',
            chart_plantuml TEXT,
            chart_error TEXT,
            documents TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    # Add columns to existing databases that predate this schema
    for col, definition in [
        ("chart_status", "TEXT NOT NULL DEFAULT 'none'"),
        ("chart_plantuml", "TEXT"),
        ("chart_error", "TEXT"),
        ("documents", "TEXT NOT NULL DEFAULT '[]'"),
        ("summary", "TEXT"),
    ]:
        try:
            _conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {definition}")
        except Exception:
            pass  # Column already exists
    _conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a dict, deserializing JSON fields."""
    d = dict(row)
    for key in ("result", "outcomes", "documents", "summary"):
        if d.get(key) is not None:
            d[key] = json.loads(d[key])
        elif key in ("outcomes", "documents"):
            d[key] = []
    return d


def create_job(job_id: str, file_path: str, original_filename: str) -> dict[str, Any]:
    """Create a new job with status='pending'."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO jobs (id, file_path, original_filename) VALUES (?, ?, ?)",
        (job_id, file_path, original_filename),
    )
    conn.commit()
    return get_job(job_id)  # type: ignore[return-value]


def update_job(job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Update job fields."""
    conn = _get_conn()
    # Serialize JSON fields
    for key in ("result", "outcomes", "documents", "summary"):
        if key in kwargs:
            kwargs[key] = json.dumps(kwargs[key])

    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    cursor = conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", values)
    if cursor.rowcount == 0:
        raise KeyError(f"Job {job_id} not found")
    conn.commit()
    return get_job(job_id)  # type: ignore[return-value]


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return job or None."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.row_factory = None
    if row is None:
        return None
    return _row_to_dict(row)


def list_jobs() -> list[dict[str, Any]]:
    """Return all jobs."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs").fetchall()
    conn.row_factory = None
    return [_row_to_dict(row) for row in rows]


def delete_job(job_id: str) -> bool:
    """Delete a job. Returns True if deleted, False if not found."""
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    return cursor.rowcount > 0
