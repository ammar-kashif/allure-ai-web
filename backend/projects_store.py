"""SQLite-backed projects store.

Projects are first-class containers for recordings. They're referenced from
dispatches (already has `project_id`), jobs (added here as a nullable FK),
ghost conversations, and entity mentions.

Piggy-backs on the connection opened by `storage.init_db()`.
"""

import datetime as dt
import sqlite3
import uuid
from typing import Any, Optional

import storage


def init() -> None:
    """Create the projects table and add project_id to jobs if missing.

    Also backfills `projects` from distinct project_id values found in
    dispatches (and jobs, once the column exists). Idempotent.
    """
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            archived_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_active "
        "ON projects(archived_at) WHERE archived_at IS NULL"
    )

    # Add project_id column to jobs if missing. SQLite has no ADD COLUMN IF
    # NOT EXISTS, so PRAGMA-inspect first.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "project_id" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN project_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id)")

    conn.commit()
    _backfill_from_dispatches()


def _backfill_from_dispatches() -> None:
    """Materialize a projects row for every distinct dispatches.project_id
    that isn't already present, and link jobs to projects via the dispatch
    row that created them (dispatches.recording_id == jobs.id).
    """
    conn = storage._get_conn()
    # dispatches table may not exist yet if dispatch_store.init() hasn't run.
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "dispatches" not in tables:
        return

    rows = conn.execute(
        "SELECT DISTINCT project_id FROM dispatches WHERE project_id IS NOT NULL"
    ).fetchall()
    for (project_id,) in rows:
        existing = conn.execute(
            "SELECT 1 FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if existing:
            continue
        now = _now_iso()
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, project_id, "Backfilled from dispatch", now, now),
        )

    # Link jobs to their project via the dispatch that produced them.
    conn.execute(
        """
        UPDATE jobs
        SET project_id = (
            SELECT d.project_id FROM dispatches d
            WHERE d.recording_id = jobs.id AND d.project_id IS NOT NULL
        )
        WHERE project_id IS NULL
          AND id IN (SELECT recording_id FROM dispatches WHERE project_id IS NOT NULL)
        """
    )
    conn.commit()


def _now_iso() -> str:
    """Match SQLite strftime('%Y-%m-%dT%H:%M:%fZ', 'now') format (ms precision)
    so string-ordered comparisons against default-populated rows are correct."""
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def create(name: str, description: str = "") -> dict[str, Any]:
    """Create a new project."""
    project_id = str(uuid.uuid4())
    now = _now_iso()
    conn = storage._get_conn()
    conn.execute(
        "INSERT INTO projects (id, name, description, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, name, description, now, now),
    )
    conn.commit()
    return get(project_id)  # type: ignore[return-value]


def get(project_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def list_active() -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM projects WHERE archived_at IS NULL ORDER BY updated_at DESC"
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def list_all() -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY updated_at DESC"
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def update(project_id: str, **fields: Any) -> dict[str, Any]:
    allowed = {"name", "description", "archived_at"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Cannot update fields: {bad}")
    if not fields:
        existing = get(project_id)
        if existing is None:
            raise KeyError(f"Project {project_id} not found")
        return existing
    fields["updated_at"] = _now_iso()
    conn = storage._get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [project_id]
    cursor = conn.execute(
        f"UPDATE projects SET {sets} WHERE id = ?", values
    )
    if cursor.rowcount == 0:
        raise KeyError(f"Project {project_id} not found")
    conn.commit()
    return get(project_id)  # type: ignore[return-value]


def archive(project_id: str) -> dict[str, Any]:
    return update(project_id, archived_at=_now_iso())


def delete(project_id: str) -> bool:
    conn = storage._get_conn()
    cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    return cursor.rowcount > 0
