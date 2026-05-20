"""Phase 4: hybrid retrieval (vector + FTS + structured + RRF fusion).

Embedding tests use a deterministic fake embedder so CI doesn't pay the
sentence-transformers download/load cost. Tests that need the real model
are marked and skipped unless GHOST_REAL_EMBEDDINGS=1.
"""

import os
from unittest.mock import patch

import numpy as np
import pytest

import projects_store
import segments_store
import storage
from entities import store as entities_store
from ghost import embeddings as ghost_embeddings
from ghost.retrieval import (
    FTSRetriever,
    HybridRetriever,
    Scope,
    StructuredRetriever,
    VectorRetriever,
    reciprocal_rank_fusion,
)
from meeting_bot import dispatch_store


@pytest.fixture(autouse=True)
def init_phase4(reset_state):
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    entities_store.init()
    ghost_embeddings.init()


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_scope_global_is_passthrough():
    where, params = Scope().where_clause()
    assert where == "1=1"
    assert params == []


def test_scope_recording_ids():
    s = Scope(recording_ids=["r1", "r2"])
    where, params = s.where_clause()
    assert "recording_id IN" in where
    assert params == ["r1", "r2"]


def test_scope_project_ids_uses_jobs_subselect():
    s = Scope(project_ids=["p1"])
    where, params = s.where_clause()
    assert "SELECT id FROM jobs WHERE project_id IN" in where
    assert params == ["p1"]


def test_scope_since_until():
    s = Scope(since_iso="2024-01-01T00:00:00Z", until_iso="2024-12-31T23:59:59Z")
    where, params = s.where_clause(created_col="created_at")
    assert "created_at >= ?" in where
    assert "created_at <= ?" in where
    assert params == ["2024-01-01T00:00:00Z", "2024-12-31T23:59:59Z"]


# ---------------------------------------------------------------------------
# RRF
# ---------------------------------------------------------------------------


def test_rrf_doc_in_both_ranks_above_either():
    a = {"source_type": "segment", "recording_id": "r", "segment_index": 0, "text": "shared"}
    b = {"source_type": "segment", "recording_id": "r", "segment_index": 1, "text": "fts-only"}
    c = {"source_type": "segment", "recording_id": "r", "segment_index": 2, "text": "vec-only"}
    fts = [a, b]
    vec = [a, c]
    merged = reciprocal_rank_fusion(fts, vec, top_k=3)
    assert merged[0]["segment_index"] == 0  # appears in both
    ids = [m["segment_index"] for m in merged]
    assert ids[0] == 0


def test_rrf_score_field_present():
    a = {"source_type": "segment", "recording_id": "r", "segment_index": 0}
    merged = reciprocal_rank_fusion([a], top_k=1)
    assert "rrf_score" in merged[0]


# ---------------------------------------------------------------------------
# FTS retriever
# ---------------------------------------------------------------------------


def _populate_recording(rid: str, segments: list[dict], project_id: str | None = None):
    storage.create_job(rid, f"/tmp/{rid}.wav", f"{rid}.wav")
    if project_id:
        storage._get_conn().execute(
            "UPDATE jobs SET project_id = ? WHERE id = ?", (project_id, rid)
        )
        storage._get_conn().commit()
    storage.update_job(rid, status="completed", result={"segments": segments})


def test_fts_finds_literal_dollar_token():
    _populate_recording("rec-money", [
        {"start": 0, "end": 1, "speaker": "John", "text": "We agreed on $400 for the quote."},
        {"start": 1, "end": 2, "speaker": "Sara", "text": "Sounds reasonable."},
    ])
    hits = FTSRetriever().search_segments("$400 quotation", k=5)
    assert any("$400" in h["text"] for h in hits)
    assert hits[0]["source_type"] == "segment"


def test_fts_segments_scope_filters_by_recording():
    _populate_recording("rec-a", [{"start": 0, "end": 1, "text": "pricing discussion"}])
    _populate_recording("rec-b", [{"start": 0, "end": 1, "text": "pricing discussion"}])
    hits = FTSRetriever().search_segments(
        "pricing", scope=Scope(recording_ids=["rec-a"]), k=5
    )
    assert all(h["recording_id"] == "rec-a" for h in hits)


def test_fts_returns_empty_for_meaningless_query():
    _populate_recording("rec-1", [{"start": 0, "end": 1, "text": "hello world"}])
    assert FTSRetriever().search_segments("", k=5) == []
    assert FTSRetriever().search_segments("***", k=5) == []


def test_fts_attachments():
    storage.create_attachment(
        "att-1", "rec-1", "design.pdf", "pdf", 100,
        extracted_text="The OAuth2 flow includes refresh tokens.",
    )
    hits = FTSRetriever().search_attachments("OAuth2 refresh", k=5)
    assert hits
    assert hits[0]["attachment_id"] == "att-1"


def test_fts_outcomes_with_type_filter():
    entities_store.index_outcomes("rec-1", [
        {"id": "o1", "type": "decision", "title": "Approve quote", "detail": "$400 budget."},
        {"id": "o2", "type": "blocker", "title": "Vendor delay", "detail": "Acme is slow."},
    ])
    hits = FTSRetriever().search_outcomes("quote", outcome_type="decision", limit=5)
    assert len(hits) == 1
    assert hits[0]["outcome_id"] == "o1"


# ---------------------------------------------------------------------------
# Vector retriever (with mocked embeddings)
# ---------------------------------------------------------------------------


def _fake_embed(texts: list[str]) -> np.ndarray:
    """Deterministic toy embedding: simple bag-of-keywords vector."""
    keywords = ["pricing", "quote", "$400", "auth", "design", "acme", "jason", "sara"]
    out = np.zeros((len(texts), 384), dtype=np.float32)
    for i, t in enumerate(texts):
        low = t.lower()
        for j, kw in enumerate(keywords):
            if kw in low:
                # spread one keyword across multiple dims so norm > 0
                out[i, j * 4:(j + 1) * 4] = 1.0
        # normalize
        n = float(np.linalg.norm(out[i]))
        if n > 0:
            out[i] /= n
        else:
            out[i, 0] = 1.0  # avoid zero vec
    return out


def test_vector_retriever_returns_empty_when_unsupported():
    """If sqlite-vec didn't load, vector search must no-op (FTS still works)."""
    with patch.object(VectorRetriever, "_supported", return_value=False):
        v = VectorRetriever()
        assert v.search_segments("anything") == []
        assert v.search_attachments("anything") == []


def test_vector_retriever_finds_close_segment():
    if not ghost_embeddings.vec_search_supported():
        pytest.skip("sqlite-vec not loaded into this connection")
    _populate_recording("rec-v", [
        {"start": 0, "end": 1, "speaker": "John", "text": "We discussed pricing for Acme."},
        {"start": 1, "end": 2, "speaker": "Sara", "text": "The auth design is solid."},
    ])
    with patch.object(ghost_embeddings, "embed_texts", side_effect=_fake_embed):
        # Manually embed the segments using our fake embedder.
        ghost_embeddings.embed_and_index_recording("rec-v")
        hits = VectorRetriever().search_segments("pricing for Acme", k=5)
    assert hits
    assert hits[0]["text"].startswith("We discussed pricing")


# ---------------------------------------------------------------------------
# Hybrid
# ---------------------------------------------------------------------------


def test_hybrid_falls_back_to_fts_when_vector_unsupported():
    _populate_recording("rec-h", [
        {"start": 0, "end": 1, "speaker": "John", "text": "Quote came in at $400."},
    ])
    with patch.object(VectorRetriever, "_supported", return_value=False):
        hits = HybridRetriever().search_transcripts("$400", k=5)
    assert hits
    assert "rrf_score" in hits[0]


def test_hybrid_outcomes_no_query_returns_structured():
    # Pre-populate outcomes both in jobs.outcomes (source of truth) AND
    # outcomes_fts (for parity); the structured path is what we're
    # verifying.
    storage.create_job("rec-1", "/tmp/a.wav", "a.wav")
    storage.update_job(
        "rec-1", status="completed",
        result={"segments": []},
        outcomes=[
            {"id": "o1", "type": "decision", "title": "Buy Acme", "detail": ""},
            {"id": "o2", "type": "blocker", "title": "Block X", "detail": ""},
        ],
    )
    entities_store.index_outcomes("rec-1", [
        {"id": "o1", "type": "decision", "title": "Buy Acme", "detail": ""},
        {"id": "o2", "type": "blocker", "title": "Block X", "detail": ""},
    ])
    h = HybridRetriever()
    hits = h.search_outcomes(None, outcome_type="decision")
    assert hits
    assert all(x["type"] == "decision" for x in hits)


def test_hybrid_outcomes_no_query_works_with_empty_fts():
    """Bug 1+2 regression: legacy recordings whose outcomes_fts was never
    populated must still return outcomes for structured queries (read
    directly from jobs.outcomes JSON)."""
    storage.create_job("rec-legacy", "/tmp/a.wav", "a.wav")
    storage.update_job(
        "rec-legacy", status="completed",
        result={"segments": []},
        outcomes=[
            {"id": "o1", "type": "decision", "title": "Stay in Business", "detail": ""},
            {"id": "o2", "type": "action_item", "title": "Hire CFO", "detail": ""},
        ],
    )
    # Intentionally skip index_outcomes -- outcomes_fts stays empty.
    h = HybridRetriever()
    hits = h.search_outcomes(None, outcome_type="decision")
    assert any(x["outcome_id"] == "o1" for x in hits)


def test_hybrid_outcomes_keyword_falls_back_to_structured_when_indexes_empty():
    """If FTS + vector both return empty, an outcome_type filter still
    finds rows via the structured fallback."""
    storage.create_job("rec-fallback", "/tmp/a.wav", "a.wav")
    storage.update_job(
        "rec-fallback", status="completed",
        result={"segments": []},
        outcomes=[
            {"id": "o9", "type": "blocker", "title": "Vendor risk", "detail": ""},
        ],
    )
    # FTS empty (no index_outcomes call). Vector also empty for outcomes.
    h = HybridRetriever()
    hits = h.search_outcomes("vendor", outcome_type="blocker")
    assert any(x["outcome_id"] == "o9" for x in hits)


def test_backfill_outcomes_fts_all_idempotent():
    """The startup backfill should populate outcomes_fts from jobs.outcomes
    for legacy recordings, and re-running it is a no-op semantically."""
    storage.create_job("rec-bf1", "/tmp/a.wav", "a.wav")
    storage.update_job(
        "rec-bf1", status="completed",
        result={"segments": []},
        outcomes=[{"id": "ox", "type": "decision", "title": "Adopt Postgres", "detail": ""}],
    )
    n1 = entities_store.backfill_outcomes_fts_all()
    assert n1 >= 1
    conn = storage._get_conn()
    rows = conn.execute("SELECT outcome_id FROM outcomes_fts WHERE recording_id = ?", ("rec-bf1",)).fetchall()
    assert len(rows) == 1
    # Run again; row count must stay at 1 (idempotent replace).
    entities_store.backfill_outcomes_fts_all()
    rows = conn.execute("SELECT outcome_id FROM outcomes_fts WHERE recording_id = ?", ("rec-bf1",)).fetchall()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Structured retriever
# ---------------------------------------------------------------------------


def test_structured_recent_activity_joins_recording_title():
    storage.create_job("rec-s", "/tmp/x.wav", "weekly-sync.wav")
    storage.update_job(
        "rec-s",
        status="completed",
        result={"meeting_title": "Pricing review", "duration": 600, "segments": []},
    )
    e = entities_store.create_entity("person", "Jason")
    entities_store.add_mention(
        e["id"], "segment", "rec-s:0", recording_id="rec-s", timestamp=10.0,
        speaker="Sara", snippet="Jason proposed $400",
    )
    s = StructuredRetriever()
    out = s.list_recent_activity(e["id"])
    assert len(out) == 1
    assert out[0]["recording_title"] == "Pricing review"


def test_structured_list_outcomes_scoped_by_project():
    storage.create_job("rec-p1", "/tmp/a.wav", "a.wav")
    storage._get_conn().execute("UPDATE jobs SET project_id = 'proj-A' WHERE id = 'rec-p1'")
    storage.create_job("rec-p2", "/tmp/b.wav", "b.wav")
    storage._get_conn().execute("UPDATE jobs SET project_id = 'proj-B' WHERE id = 'rec-p2'")
    storage._get_conn().commit()
    storage.update_job(
        "rec-p1", status="completed", result={"segments": []},
        outcomes=[{"id": "oa", "type": "decision", "title": "A!", "detail": ""}],
    )
    storage.update_job(
        "rec-p2", status="completed", result={"segments": []},
        outcomes=[{"id": "ob", "type": "decision", "title": "B!", "detail": ""}],
    )
    s = StructuredRetriever()
    hits = s.list_outcomes(scope=Scope(project_ids=["proj-A"]))
    assert {h["outcome_id"] for h in hits} == {"oa"}


def test_structured_list_recordings_global():
    storage.create_job("rec-r1", "/tmp/r1.wav", "r1.wav")
    storage.update_job("rec-r1", status="completed", result={"meeting_title": "Sync 1", "segments": [], "duration": 60})
    storage.create_job("rec-r2", "/tmp/r2.wav", "r2.wav")
    storage.update_job("rec-r2", status="completed", result={"meeting_title": "Sync 2", "segments": [], "duration": 120})
    out = StructuredRetriever().list_recordings()
    ids = {r["recording_id"] for r in out}
    assert {"rec-r1", "rec-r2"}.issubset(ids)
