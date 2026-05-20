"""Eval-set storage + run history.

eval_queries:   one row per generated query with expected source(s)
eval_runs:      one row per replay of an eval_query, with metrics
"""

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
        CREATE TABLE IF NOT EXISTS eval_queries (
            id              TEXT PRIMARY KEY,
            question        TEXT NOT NULL,
            kind            TEXT NOT NULL,
            expected_sources TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eval_runs (
            id              TEXT PRIMARY KEY,
            query_id        TEXT NOT NULL REFERENCES eval_queries(id) ON DELETE CASCADE,
            answer          TEXT NOT NULL,
            cited_sources   TEXT NOT NULL,
            tokens_in       INTEGER,
            tokens_out      INTEGER,
            cost_usd        REAL,
            latency_ms      INTEGER,
            primary_citation_correct INTEGER,
            recall_at_k     REAL,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_eval_runs_query ON eval_runs(query_id, created_at)"
    )
    conn.commit()


def _now_iso() -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def add_query(question: str, kind: str, expected_sources: list[dict[str, Any]]) -> dict[str, Any]:
    qid = str(uuid.uuid4())
    conn = storage._get_conn()
    conn.execute(
        "INSERT INTO eval_queries (id, question, kind, expected_sources) VALUES (?, ?, ?, ?)",
        (qid, question, kind, json.dumps(expected_sources)),
    )
    conn.commit()
    return get_query(qid)  # type: ignore[return-value]


def get_query(qid: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM eval_queries WHERE id = ?", (qid,)).fetchone()
    conn.row_factory = None
    if not row:
        return None
    d = dict(row)
    d["expected_sources"] = json.loads(d["expected_sources"])
    return d


def list_queries(limit: int = 200) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM eval_queries ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        d = dict(r)
        d["expected_sources"] = json.loads(d["expected_sources"])
        out.append(d)
    return out


def record_run(
    query_id: str,
    *,
    answer: str,
    cited_sources: list[dict[str, Any]],
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    latency_ms: int,
    primary_citation_correct: bool,
    recall_at_k: float,
) -> dict[str, Any]:
    rid = str(uuid.uuid4())
    conn = storage._get_conn()
    conn.execute(
        """
        INSERT INTO eval_runs (
            id, query_id, answer, cited_sources,
            tokens_in, tokens_out, cost_usd, latency_ms,
            primary_citation_correct, recall_at_k
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rid, query_id, answer, json.dumps(cited_sources),
            tokens_in, tokens_out, cost_usd, latency_ms,
            1 if primary_citation_correct else 0, float(recall_at_k),
        ),
    )
    conn.commit()
    return {"id": rid}


def list_runs(query_id: Optional[str] = None, limit: int = 200) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    if query_id:
        rows = conn.execute(
            "SELECT * FROM eval_runs WHERE query_id = ? ORDER BY created_at DESC LIMIT ?",
            (query_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        d = dict(r)
        d["cited_sources"] = json.loads(d["cited_sources"])
        d["primary_citation_correct"] = bool(d["primary_citation_correct"])
        out.append(d)
    return out


def stats(window_hours: int = 24 * 7) -> dict[str, Any]:
    """Aggregate eval-run health over a window. Powers the latency
    regression check + the cost dashboard."""
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=window_hours)
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM eval_runs WHERE created_at >= ?",
        (since.strftime("%Y-%m-%dT%H:%M:%S.000Z"),),
    ).fetchall()
    conn.row_factory = None
    if not rows:
        return {
            "count": 0,
            "window_hours": window_hours,
        }
    lats = sorted(int(r["latency_ms"]) for r in rows if r["latency_ms"] is not None)
    costs = [float(r["cost_usd"]) for r in rows if r["cost_usd"] is not None]
    recalls = [float(r["recall_at_k"]) for r in rows if r["recall_at_k"] is not None]
    corr = [bool(r["primary_citation_correct"]) for r in rows]
    p95_idx = max(0, int(round(0.95 * len(lats))) - 1) if lats else 0
    return {
        "count": len(rows),
        "window_hours": window_hours,
        "latency_p50_ms": lats[len(lats) // 2] if lats else 0,
        "latency_p95_ms": lats[p95_idx] if lats else 0,
        "cost_avg_usd": round(sum(costs) / len(costs), 4) if costs else 0,
        "cost_total_usd": round(sum(costs), 4) if costs else 0,
        "recall_at_k_avg": round(sum(recalls) / len(recalls), 4) if recalls else 0,
        "primary_citation_correct_rate": round(
            sum(corr) / len(corr), 4
        ) if corr else 0,
    }
