"""FTS5-backed full-text retriever.

FTS5 is what finds literal tokens like '$400' or 'OAuth2' that vector
search smears. The hybrid layer fuses FTS rank with vector rank.

Source tables:
    segments_fts        -- transcript segments
    attachments_fts     -- attachment chunks (whole-doc currently; chunked
                           when attachment_vec_map populates with multiple
                           rows -- separate concern from FTS)
    outcomes_fts        -- extracted outcomes
"""

import re
import sqlite3
from typing import Any, Optional

import storage

from .scope import Scope


def _escape_fts(query: str) -> str:
    """Sanitize a user query for FTS5 MATCH.

    FTS5 syntax has lots of special chars; the safest move is to quote
    each non-empty token. We also strip operators that would let a user
    cause expensive queries.
    """
    # Pull out simple words (alphanum + _ + ' + -)
    tokens = re.findall(r"[A-Za-z0-9_'-]+|\$[\d,]+(?:\.\d+)?", query)
    if not tokens:
        return ""
    # Quote each token to avoid FTS5 operator interpretation. Use OR
    # combination so any token can match (better recall for short queries).
    quoted = [f'"{t}"' for t in tokens if t]
    return " OR ".join(quoted)


class FTSRetriever:
    """Search over the three FTS5 virtual tables."""

    def search_segments(
        self, query: str, scope: Optional[Scope] = None, k: int = 10
    ) -> list[dict[str, Any]]:
        match = _escape_fts(query)
        if not match:
            return []
        scope = scope or Scope()
        where, params = scope.where_clause(recording_col="s.recording_id")
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        sql = (
            "SELECT s.recording_id, s.segment_index, s.speaker, s.text, s.start_seconds, "
            "    bm25(segments_fts) AS rank "
            "FROM segments_fts "
            "JOIN segments s ON s.recording_id = segments_fts.recording_id "
            "    AND s.segment_index = segments_fts.segment_index "
            "WHERE segments_fts MATCH ? "
            f"    AND {where} "
            "ORDER BY rank "
            "LIMIT ?"
        )
        rows = conn.execute(sql, [match, *params, k]).fetchall()
        conn.row_factory = None
        out = []
        for r in rows:
            d = dict(r)
            out.append({
                "source_type": "segment",
                "recording_id": d["recording_id"],
                "segment_index": d["segment_index"],
                "speaker": d["speaker"],
                "text": d["text"],
                "timestamp": d["start_seconds"],
                "rank": float(d["rank"]),
            })
        return out

    def search_attachments(
        self, query: str, scope: Optional[Scope] = None, k: int = 5
    ) -> list[dict[str, Any]]:
        match = _escape_fts(query)
        if not match:
            return []
        scope = scope or Scope()
        where, params = scope.where_clause()
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        sql = (
            "SELECT attachment_id, recording_id, filename, "
            "    substr(text, 1, 400) AS snippet, "
            "    bm25(attachments_fts) AS rank "
            "FROM attachments_fts "
            "WHERE attachments_fts MATCH ? "
            f"    AND {where} "
            "ORDER BY rank "
            "LIMIT ?"
        )
        rows = conn.execute(sql, [match, *params, k]).fetchall()
        conn.row_factory = None
        return [
            {
                "source_type": "attachment",
                "attachment_id": r["attachment_id"],
                "recording_id": r["recording_id"],
                "filename": r["filename"],
                "snippet": r["snippet"],
                "rank": float(r["rank"]),
            }
            for r in rows
        ]

    def search_outcomes(
        self,
        query: Optional[str],
        scope: Optional[Scope] = None,
        outcome_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        scope = scope or Scope()
        where, params = scope.where_clause()
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        if query:
            match = _escape_fts(query)
            if not match:
                return []
            sql_parts = [
                "SELECT outcome_id, recording_id, type, title, detail, "
                "    bm25(outcomes_fts) AS rank "
                "FROM outcomes_fts "
                "WHERE outcomes_fts MATCH ?"
            ]
            args = [match]
            sql_parts.append(f"AND {where}")
            args.extend(params)
            if outcome_type:
                sql_parts.append("AND type = ?")
                args.append(outcome_type)
            sql_parts.append("ORDER BY rank LIMIT ?")
            args.append(limit)
            sql = " ".join(sql_parts)
        else:
            # No FTS query: pure structured filter (still scoped).
            sql_parts = [
                "SELECT outcome_id, recording_id, type, title, detail, NULL AS rank "
                "FROM outcomes_fts "
                f"WHERE {where}"
            ]
            args = list(params)
            if outcome_type:
                sql_parts.append("AND type = ?")
                args.append(outcome_type)
            sql_parts.append("LIMIT ?")
            args.append(limit)
            sql = " ".join(sql_parts)
        rows = conn.execute(sql, args).fetchall()
        conn.row_factory = None
        return [
            {
                "source_type": "outcome",
                "outcome_id": r["outcome_id"],
                "recording_id": r["recording_id"],
                "type": r["type"],
                "title": r["title"],
                "detail": r["detail"],
                "rank": float(r["rank"]) if r["rank"] is not None else None,
            }
            for r in rows
        ]
