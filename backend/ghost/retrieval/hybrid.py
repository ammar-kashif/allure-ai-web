"""Hybrid retriever: fuse vector + FTS rankings via Reciprocal Rank Fusion.

Why RRF: tuning-free, robust to score scale differences (FTS bm25 is
negative; vector distance is positive), well-studied. score(doc) =
Σ 1/(k + rank_i) across the ranked lists doc appears in, with k=60 the
common default. We can swap to learned-fusion later.
"""

import logging
from typing import Any, Optional

from .fts import FTSRetriever
from .scope import Scope
from .structured import StructuredRetriever
from .vector import VectorRetriever

logger = logging.getLogger(__name__)


def _identity(row: dict[str, Any]) -> tuple:
    """Stable identity per source row across retrievers."""
    st = row["source_type"]
    if st == "segment":
        return ("segment", row["recording_id"], row["segment_index"])
    if st == "outcome":
        return ("outcome", row["outcome_id"])
    if st == "attachment":
        return ("attachment", row["attachment_id"], row.get("chunk_index", 0))
    return (st, repr(row))


def reciprocal_rank_fusion(
    *ranked_lists: list[dict[str, Any]], k: int = 60, top_k: int = 10
) -> list[dict[str, Any]]:
    """Merge multiple ranked lists into a single RRF-scored list.

    Each list is assumed to be in rank order (best first). Ties are
    broken by first appearance.
    """
    scores: dict[tuple, float] = {}
    payloads: dict[tuple, dict[str, Any]] = {}
    order: list[tuple] = []
    for lst in ranked_lists:
        for rank, row in enumerate(lst):
            ident = _identity(row)
            scores[ident] = scores.get(ident, 0.0) + 1.0 / (k + rank + 1)
            if ident not in payloads:
                payloads[ident] = row
                order.append(ident)
    ranked = sorted(order, key=lambda i: scores[i], reverse=True)
    out = []
    for ident in ranked[:top_k]:
        row = dict(payloads[ident])
        row["rrf_score"] = round(scores[ident], 6)
        out.append(row)
    return out


class HybridRetriever:
    def __init__(self, vector: Optional[VectorRetriever] = None, fts: Optional[FTSRetriever] = None):
        self.vector = vector or VectorRetriever()
        self.fts = fts or FTSRetriever()

    def search_transcripts(
        self,
        query: str,
        scope: Optional[Scope] = None,
        k: int = 8,
        *,
        speaker: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        scope = scope or Scope()
        fts_hits = self.fts.search_segments(query, scope=scope, k=max(k, 10), speaker=speaker)
        vec_hits = self.vector.search_segments(query, scope=scope, k=max(k, 10), speaker=speaker)
        return reciprocal_rank_fusion(fts_hits, vec_hits, top_k=k)

    def search_attachments(
        self, query: str, scope: Optional[Scope] = None, k: int = 5
    ) -> list[dict[str, Any]]:
        scope = scope or Scope()
        fts_hits = self.fts.search_attachments(query, scope=scope, k=max(k, 8))
        vec_hits = self.vector.search_attachments(query, scope=scope, k=max(k, 8))
        return reciprocal_rank_fusion(fts_hits, vec_hits, top_k=k)

    def search_outcomes(
        self,
        query: Optional[str],
        scope: Optional[Scope] = None,
        outcome_type: Optional[str] = None,
        k: int = 8,
    ) -> list[dict[str, Any]]:
        scope = scope or Scope()
        if not query:
            # No semantic query -> structured read directly from
            # jobs.outcomes JSON (source of truth). Works for legacy
            # recordings whose outcomes_fts was never populated.
            return StructuredRetriever().list_outcomes(
                scope=scope, outcome_type=outcome_type, limit=k,
            )
        fts_hits = self.fts.search_outcomes(query, scope=scope, outcome_type=outcome_type, limit=max(k, 8))
        vec_hits = self.vector.search_outcomes(query, scope=scope, k=max(k, 8))
        if outcome_type:
            vec_hits = [v for v in vec_hits if v.get("type") in (None, outcome_type)]
        merged = reciprocal_rank_fusion(fts_hits, vec_hits, top_k=k)
        # If both FTS and vector came back empty (legacy data with no
        # populated indexes), fall back to structured so a type filter
        # still returns something useful.
        if not merged and outcome_type:
            return StructuredRetriever().list_outcomes(
                scope=scope, outcome_type=outcome_type, limit=k,
            )
        return merged
