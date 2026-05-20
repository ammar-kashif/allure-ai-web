"""Conversation persistence for Ghost chat threads."""

import datetime as dt
import json
import sqlite3
import uuid
from typing import Any, Optional

import storage


def init() -> None:
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ghost_conversations (
            id              TEXT PRIMARY KEY,
            title           TEXT,
            project_id      TEXT,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            last_activity_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ghost_messages (
            id              TEXT PRIMARY KEY,
            conv_id         TEXT NOT NULL REFERENCES ghost_conversations(id) ON DELETE CASCADE,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            citations_json  TEXT,
            tool_calls_json TEXT,
            tokens_in       INTEGER,
            tokens_out      INTEGER,
            cost_usd        REAL,
            latency_ms      INTEGER,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ghost_messages_conv "
        "ON ghost_messages(conv_id, created_at)"
    )
    conn.commit()


def _now_iso() -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def create_conversation(title: Optional[str] = None, project_id: Optional[str] = None) -> dict[str, Any]:
    cid = str(uuid.uuid4())
    conn = storage._get_conn()
    conn.execute(
        "INSERT INTO ghost_conversations (id, title, project_id) VALUES (?, ?, ?)",
        (cid, title, project_id),
    )
    conn.commit()
    return get_conversation(cid)  # type: ignore[return-value]


def get_conversation(conv_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM ghost_conversations WHERE id = ?", (conv_id,)
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def list_conversations(limit: int = 50) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM ghost_conversations ORDER BY last_activity_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def list_messages(conv_id: str) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM ghost_messages WHERE conv_id = ? ORDER BY created_at",
        (conv_id,),
    ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        d = dict(r)
        for k in ("citations_json", "tool_calls_json"):
            if d.get(k):
                try:
                    d[k.replace("_json", "")] = json.loads(d[k])
                except Exception:
                    d[k.replace("_json", "")] = None
        out.append(d)
    return out


def append_message(
    conv_id: str,
    role: str,
    content: str,
    *,
    citations: Optional[list[dict[str, Any]]] = None,
    tool_calls: Optional[list[dict[str, Any]]] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost_usd: Optional[float] = None,
    latency_ms: Optional[int] = None,
) -> dict[str, Any]:
    mid = str(uuid.uuid4())
    conn = storage._get_conn()
    conn.execute(
        """
        INSERT INTO ghost_messages
            (id, conv_id, role, content, citations_json, tool_calls_json,
             tokens_in, tokens_out, cost_usd, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mid, conv_id, role, content,
            json.dumps(citations) if citations is not None else None,
            json.dumps(tool_calls) if tool_calls is not None else None,
            tokens_in, tokens_out, cost_usd, latency_ms,
        ),
    )
    conn.execute(
        "UPDATE ghost_conversations SET last_activity_at = ? WHERE id = ?",
        (_now_iso(), conv_id),
    )
    conn.commit()
    return {"id": mid, "conv_id": conv_id, "role": role, "content": content}


def delete_conversation(conv_id: str) -> bool:
    conn = storage._get_conn()
    cursor = conn.execute("DELETE FROM ghost_conversations WHERE id = ?", (conv_id,))
    conn.commit()
    return cursor.rowcount > 0


def month_to_date_cost_usd() -> float:
    """Sum cost_usd over the current month. Used for monthly-cap enforcement."""
    conn = storage._get_conn()
    today = dt.datetime.now(dt.timezone.utc)
    start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM ghost_messages WHERE created_at >= ?",
        (start,),
    ).fetchone()
    return float(row[0] or 0.0)
