"""SQLite-backed store for autonomy runs + actions + settings.

Three tables in the existing backend SQLite (audit lives next to the
data it audits, not in the frontend DB):

    autonomy_runs       -- one row per recording autonomy pass
    autonomy_actions    -- per-action audit rows
    autonomy_settings   -- single-row config

Patterns mirror `projects_store.py` (storage._get_conn reuse).
"""

import datetime as dt
import json
import sqlite3
import uuid
from typing import Any, Iterable, Optional

import storage

VALID_KINDS = {
    "task_created",
    "task_discussed",
    "task_appears_done",
    "task_appears_blocked",
    "skipped_duplicate",
    "skipped_verifier",
    "skipped_gate",
}

VALID_STATUSES = {"running", "completed", "failed", "skipped"}
VALID_SKIP_REASONS = {
    "no_project",
    "first_in_project",
    "too_short",
    "disabled_global",
    "disabled_project",
    "cap_reached",
}


def init() -> None:
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_runs (
            id TEXT PRIMARY KEY,
            recording_id TEXT NOT NULL,
            project_id TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            skip_reason TEXT,
            detect_tokens_in INTEGER,
            detect_tokens_out INTEGER,
            verify_tokens_in INTEGER,
            verify_tokens_out INTEGER,
            cost_usd REAL,
            tasks_created INTEGER NOT NULL DEFAULT 0,
            tasks_discussed INTEGER NOT NULL DEFAULT 0,
            follow_up_to_json TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            completed_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_autonomy_runs_recording "
        "ON autonomy_runs(recording_id, created_at DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_actions (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES autonomy_runs(id) ON DELETE CASCADE,
            recording_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            target_task_id TEXT,
            segment_index INTEGER,
            speaker TEXT,
            reason TEXT NOT NULL DEFAULT '',
            verifier_reason TEXT,
            detector_payload_json TEXT NOT NULL DEFAULT '{}',
            reversed_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_autonomy_actions_recording "
        "ON autonomy_actions(recording_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_autonomy_actions_run "
        "ON autonomy_actions(run_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 1,
            monthly_cap_usd REAL NOT NULL DEFAULT 10.0,
            disabled_project_ids TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO autonomy_settings (id) VALUES (1)")
    conn.commit()


def _now_iso() -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------


def create_run(
    recording_id: str,
    project_id: Optional[str],
    *,
    status: str = "running",
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")
    rid = str(uuid.uuid4())
    conn = storage._get_conn()
    conn.execute(
        "INSERT INTO autonomy_runs (id, recording_id, project_id, status) "
        "VALUES (?, ?, ?, ?)",
        (rid, recording_id, project_id, status),
    )
    conn.commit()
    return get_run(rid)  # type: ignore[return-value]


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM autonomy_runs WHERE id = ?", (run_id,)
    ).fetchone()
    conn.row_factory = None
    if not row:
        return None
    d = dict(row)
    d["follow_up_to"] = json.loads(d.pop("follow_up_to_json") or "[]")
    return d


def get_latest_run_for_recording(recording_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM autonomy_runs WHERE recording_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (recording_id,),
    ).fetchone()
    conn.row_factory = None
    if not row:
        return None
    d = dict(row)
    d["follow_up_to"] = json.loads(d.pop("follow_up_to_json") or "[]")
    return d


def update_run(run_id: str, **fields: Any) -> dict[str, Any]:
    if "status" in fields and fields["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {fields['status']!r}")
    if "skip_reason" in fields and fields["skip_reason"] is not None and fields["skip_reason"] not in VALID_SKIP_REASONS:
        raise ValueError(f"Invalid skip_reason: {fields['skip_reason']!r}")
    if "follow_up_to" in fields:
        fields["follow_up_to_json"] = json.dumps(fields.pop("follow_up_to") or [])
    conn = storage._get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [run_id]
    cursor = conn.execute(
        f"UPDATE autonomy_runs SET {sets} WHERE id = ?", values
    )
    if cursor.rowcount == 0:
        raise KeyError(f"Run {run_id} not found")
    conn.commit()
    return get_run(run_id)  # type: ignore[return-value]


def mark_skipped(
    recording_id: str,
    project_id: Optional[str],
    skip_reason: str,
) -> dict[str, Any]:
    """Convenience: create a skipped run in one call."""
    run = create_run(recording_id, project_id, status="skipped")
    return update_run(
        run["id"],
        skip_reason=skip_reason,
        completed_at=_now_iso(),
    )


def list_runs(limit: int = 100) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM autonomy_runs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        d = dict(r)
        d["follow_up_to"] = json.loads(d.pop("follow_up_to_json") or "[]")
        out.append(d)
    return out


def month_to_date_cost_usd() -> float:
    conn = storage._get_conn()
    today = dt.datetime.now(dt.timezone.utc)
    start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM autonomy_runs WHERE created_at >= ?",
        (start,),
    ).fetchone()
    return float(row[0] or 0.0)


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------


def add_action(
    run_id: str,
    recording_id: str,
    kind: str,
    *,
    target_task_id: Optional[str] = None,
    segment_index: Optional[int] = None,
    speaker: Optional[str] = None,
    reason: str = "",
    verifier_reason: Optional[str] = None,
    detector_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid action kind: {kind!r}")
    aid = str(uuid.uuid4())
    conn = storage._get_conn()
    conn.execute(
        """
        INSERT INTO autonomy_actions (
            id, run_id, recording_id, kind, target_task_id,
            segment_index, speaker, reason, verifier_reason,
            detector_payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            aid,
            run_id,
            recording_id,
            kind,
            target_task_id,
            segment_index,
            speaker,
            reason,
            verifier_reason,
            json.dumps(detector_payload or {}),
        ),
    )
    if kind == "task_created":
        conn.execute(
            "UPDATE autonomy_runs SET tasks_created = tasks_created + 1 WHERE id = ?",
            (run_id,),
        )
    elif kind in ("task_discussed", "task_appears_done", "task_appears_blocked"):
        conn.execute(
            "UPDATE autonomy_runs SET tasks_discussed = tasks_discussed + 1 WHERE id = ?",
            (run_id,),
        )
    conn.commit()
    return get_action(aid)  # type: ignore[return-value]


def get_action(action_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM autonomy_actions WHERE id = ?", (action_id,)
    ).fetchone()
    conn.row_factory = None
    if not row:
        return None
    d = dict(row)
    d["detector_payload"] = json.loads(d.pop("detector_payload_json") or "{}")
    return d


def list_actions(run_id: str) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM autonomy_actions WHERE run_id = ? ORDER BY created_at",
        (run_id,),
    ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        d = dict(r)
        d["detector_payload"] = json.loads(d.pop("detector_payload_json") or "{}")
        out.append(d)
    return out


def list_actions_for_recording(recording_id: str) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM autonomy_actions WHERE recording_id = ? "
        "ORDER BY created_at DESC",
        (recording_id,),
    ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        d = dict(r)
        d["detector_payload"] = json.loads(d.pop("detector_payload_json") or "{}")
        out.append(d)
    return out


def mark_action_reversed(action_id: str) -> dict[str, Any]:
    conn = storage._get_conn()
    action = get_action(action_id)
    if action is None:
        raise KeyError(f"Action {action_id} not found")
    if action.get("reversed_at"):
        return action
    conn.execute(
        "UPDATE autonomy_actions SET reversed_at = ? WHERE id = ?",
        (_now_iso(), action_id),
    )
    # Adjust parent run counters.
    if action["kind"] == "task_created":
        conn.execute(
            "UPDATE autonomy_runs SET tasks_created = MAX(0, tasks_created - 1) WHERE id = ?",
            (action["run_id"],),
        )
    elif action["kind"] in ("task_discussed", "task_appears_done", "task_appears_blocked"):
        conn.execute(
            "UPDATE autonomy_runs SET tasks_discussed = MAX(0, tasks_discussed - 1) WHERE id = ?",
            (action["run_id"],),
        )
    conn.commit()
    return get_action(action_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


def get_settings() -> dict[str, Any]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM autonomy_settings WHERE id = 1").fetchone()
    conn.row_factory = None
    if not row:
        return {
            "enabled": True,
            "monthly_cap_usd": 10.0,
            "disabled_project_ids": [],
        }
    d = dict(row)
    d["enabled"] = bool(d["enabled"])
    d["disabled_project_ids"] = json.loads(d["disabled_project_ids"] or "[]")
    d.pop("id", None)
    return d


def update_settings(
    *,
    enabled: Optional[bool] = None,
    monthly_cap_usd: Optional[float] = None,
    disabled_project_ids: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if enabled is not None:
        fields["enabled"] = 1 if enabled else 0
    if monthly_cap_usd is not None:
        fields["monthly_cap_usd"] = float(monthly_cap_usd)
    if disabled_project_ids is not None:
        fields["disabled_project_ids"] = json.dumps(list(disabled_project_ids))
    if not fields:
        return get_settings()
    conn = storage._get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE autonomy_settings SET {sets} WHERE id = 1",
        list(fields.values()),
    )
    conn.commit()
    return get_settings()
