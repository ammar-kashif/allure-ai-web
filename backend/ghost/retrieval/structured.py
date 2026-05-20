"""Structured (typed-row) retrievers.

Anything that doesn't need ranking: entity activity timelines, outcomes
by type, recordings list, recent mentions. Hits indexed columns directly.
"""

import sqlite3
from typing import Any, Optional

import storage
from entities import store as entities_store

from .scope import Scope


class StructuredRetriever:
    def list_recent_activity(
        self,
        entity_id: str,
        *,
        source_types: Optional[list[str]] = None,
        limit: int = 10,
        since_iso: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows = entities_store.list_mentions(
            entity_id, source_types=source_types, limit=limit, since_iso=since_iso,
        )
        # Join recording title.
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        out = []
        for r in rows:
            rec = conn.execute(
                "SELECT original_filename, "
                "    json_extract(result, '$.meeting_title') AS meeting_title, "
                "    json_extract(result, '$.duration') AS duration "
                "FROM jobs WHERE id = ?",
                (r["recording_id"],),
            ).fetchone() if r["recording_id"] else None
            d = dict(r)
            d["recording_title"] = (
                (rec["meeting_title"] if rec else None) or
                (rec["original_filename"] if rec else None) or
                "(unknown recording)"
            )
            d["recording_duration"] = float(rec["duration"]) if rec and rec["duration"] is not None else None
            out.append(d)
        conn.row_factory = None
        return out

    def list_outcomes(
        self,
        scope: Optional[Scope] = None,
        outcome_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = scope or Scope()
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        where, params = scope.where_clause(recording_col="j.id")
        sql_parts = [
            "SELECT j.id AS recording_id, j.original_filename, "
            "    json_extract(j.result, '$.meeting_title') AS meeting_title, "
            "    j.outcomes AS outcomes_json "
            "FROM jobs j "
            f"WHERE j.status = 'completed' AND {where}"
        ]
        rows = conn.execute(" ".join(sql_parts), params).fetchall()
        conn.row_factory = None
        out: list[dict[str, Any]] = []
        import json as _json
        for r in rows:
            outcomes = _json.loads(r["outcomes_json"] or "[]")
            for o in outcomes:
                if outcome_type and o.get("type") != outcome_type:
                    continue
                out.append({
                    "source_type": "outcome",
                    "outcome_id": o.get("id"),
                    "recording_id": r["recording_id"],
                    "type": o.get("type"),
                    "title": o.get("title"),
                    "detail": o.get("detail"),
                    "confidence": o.get("confidence"),
                    "recording_title": r["meeting_title"] or r["original_filename"],
                })
                if len(out) >= limit:
                    return out
        return out

    def list_recordings(
        self,
        scope: Optional[Scope] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = scope or Scope()
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        where, params = scope.where_clause(recording_col="recording_id")
        sql = (
            "SELECT * FROM v_recording_summary "
            f"WHERE {where} "
            "LIMIT ?"
        )
        rows = conn.execute(sql, [*params, limit]).fetchall()
        conn.row_factory = None
        return [dict(r) for r in rows]
