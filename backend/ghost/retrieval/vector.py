"""Vector retriever backed by sqlite-vec.

Encodes the query with the shared embedding model, queries each vec0
table, joins back to source rows for context. Gracefully no-ops when
sqlite-vec is not loaded (the FTS + structured retrievers still work).
"""

import logging
import sqlite3
from typing import Any, Optional

import numpy as np

import storage

from ghost import embeddings
from .scope import Scope

logger = logging.getLogger(__name__)


class VectorRetriever:
    def _supported(self) -> bool:
        return embeddings.vec_search_supported()

    def search_segments(
        self, query: str, scope: Optional[Scope] = None, k: int = 10
    ) -> list[dict[str, Any]]:
        if not self._supported():
            return []
        scope = scope or Scope()
        vec = embeddings.embed_texts([query])[0]
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        # vec0 returns (rowid, distance). Smaller distance = closer.
        candidate_k = max(k * 3, 50)  # over-fetch then post-filter by scope
        rows = conn.execute(
            "SELECT v.rowid, v.distance FROM segment_vecs v "
            "WHERE v.embedding MATCH ? AND k = ? "
            "ORDER BY v.distance",
            (vec.astype(np.float32).tobytes(), candidate_k),
        ).fetchall()

        out: list[dict[str, Any]] = []
        for r in rows:
            rowid = r["rowid"]
            distance = float(r["distance"])
            mapping = conn.execute(
                "SELECT recording_id, segment_index FROM segment_vec_map WHERE rowid = ?",
                (rowid,),
            ).fetchone()
            if not mapping:
                continue
            seg = conn.execute(
                "SELECT speaker, text, start_seconds FROM segments "
                "WHERE recording_id = ? AND segment_index = ?",
                (mapping["recording_id"], mapping["segment_index"]),
            ).fetchone()
            if not seg:
                continue
            # Scope filter post-hoc (cheaper than altering the vec query).
            if not _row_passes_scope(scope, conn, mapping["recording_id"]):
                continue
            out.append({
                "source_type": "segment",
                "recording_id": mapping["recording_id"],
                "segment_index": mapping["segment_index"],
                "speaker": seg["speaker"],
                "text": seg["text"],
                "timestamp": seg["start_seconds"],
                "distance": distance,
            })
            if len(out) >= k:
                break
        conn.row_factory = None
        return out

    def search_attachments(
        self, query: str, scope: Optional[Scope] = None, k: int = 5
    ) -> list[dict[str, Any]]:
        if not self._supported():
            return []
        scope = scope or Scope()
        vec = embeddings.embed_texts([query])[0]
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        candidate_k = max(k * 3, 30)
        rows = conn.execute(
            "SELECT v.rowid, v.distance FROM attachment_vecs v "
            "WHERE v.embedding MATCH ? AND k = ? "
            "ORDER BY v.distance",
            (vec.astype(np.float32).tobytes(), candidate_k),
        ).fetchall()
        out = []
        for r in rows:
            mapping = conn.execute(
                "SELECT attachment_id, recording_id, chunk_index FROM attachment_vec_map "
                "WHERE rowid = ?",
                (r["rowid"],),
            ).fetchone()
            if not mapping:
                continue
            if not _row_passes_scope(scope, conn, mapping["recording_id"]):
                continue
            att = conn.execute(
                "SELECT filename, substr(extracted_text, 1, 400) AS snippet "
                "FROM attachments WHERE id = ?",
                (mapping["attachment_id"],),
            ).fetchone()
            if not att:
                continue
            out.append({
                "source_type": "attachment",
                "attachment_id": mapping["attachment_id"],
                "recording_id": mapping["recording_id"],
                "chunk_index": mapping["chunk_index"],
                "filename": att["filename"],
                "snippet": att["snippet"],
                "distance": float(r["distance"]),
            })
            if len(out) >= k:
                break
        conn.row_factory = None
        return out

    def search_outcomes(
        self, query: str, scope: Optional[Scope] = None, k: int = 8
    ) -> list[dict[str, Any]]:
        if not self._supported():
            return []
        scope = scope or Scope()
        vec = embeddings.embed_texts([query])[0]
        conn = storage._get_conn()
        conn.row_factory = sqlite3.Row
        candidate_k = max(k * 3, 30)
        rows = conn.execute(
            "SELECT v.rowid, v.distance FROM outcome_vecs v "
            "WHERE v.embedding MATCH ? AND k = ? "
            "ORDER BY v.distance",
            (vec.astype(np.float32).tobytes(), candidate_k),
        ).fetchall()
        out = []
        for r in rows:
            mapping = conn.execute(
                "SELECT outcome_id, recording_id FROM outcome_vec_map WHERE rowid = ?",
                (r["rowid"],),
            ).fetchone()
            if not mapping:
                continue
            if not _row_passes_scope(scope, conn, mapping["recording_id"]):
                continue
            out.append({
                "source_type": "outcome",
                "outcome_id": mapping["outcome_id"],
                "recording_id": mapping["recording_id"],
                "distance": float(r["distance"]),
            })
            if len(out) >= k:
                break
        conn.row_factory = None
        return out


def _row_passes_scope(scope: Scope, conn, recording_id: str) -> bool:
    if scope.is_global():
        return True
    if scope.recording_ids and recording_id not in scope.recording_ids:
        return False
    if scope.project_ids:
        row = conn.execute(
            "SELECT project_id FROM jobs WHERE id = ?", (recording_id,)
        ).fetchone()
        if row is None:
            return False
        if row[0] not in scope.project_ids:
            return False
    return True
