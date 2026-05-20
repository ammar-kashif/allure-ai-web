"""Phase 3: entity extraction + resolution + FTS triggers."""

import json
from types import SimpleNamespace

import pytest

import projects_store
import segments_store
import storage
from entities import store as entities_store
from entities.extractor import (
    deterministic_pre_pass,
    run_entitize,
    backfill_all_recordings,
)
from meeting_bot import dispatch_store


@pytest.fixture(autouse=True)
def init_phase3(reset_state):
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    entities_store.init()


# ---------------------------------------------------------------------------
# entities store: resolution
# ---------------------------------------------------------------------------


def test_create_and_find_by_exact_name():
    e = entities_store.create_entity("person", "Jason Wu", aliases=["Jason"])
    hit = entities_store.find_by_exact_name("Jason Wu", "person")
    assert hit["id"] == e["id"]
    # Case-insensitive
    hit = entities_store.find_by_exact_name("jason wu", "person")
    assert hit["id"] == e["id"]


def test_find_by_alias():
    e = entities_store.create_entity("person", "Jason Wu", aliases=["Jason", "JW"])
    hit = entities_store.find_by_alias("JW", "person")
    assert hit is not None
    assert hit["id"] == e["id"]


def test_resolve_or_create_reuses_exact():
    e1 = entities_store.resolve_or_create("Jason Wu", "person")
    e2 = entities_store.resolve_or_create("Jason Wu", "person")
    assert e1["id"] == e2["id"]


def test_resolve_or_create_via_alias():
    e1 = entities_store.create_entity("person", "Jason Wu", aliases=["Jason"])
    e2 = entities_store.resolve_or_create("Jason", "person")
    assert e1["id"] == e2["id"]


def test_resolve_or_create_fuzzy_high_confidence():
    entities_store.create_entity("person", "Jonathan Smith")
    e = entities_store.resolve_or_create("Jonathan  Smith", "person")  # double space
    # rapidfuzz token_set_ratio of these will be >= 95, so it should fold.
    refetched = entities_store.find_by_exact_name("Jonathan Smith", "person")
    assert e["id"] == refetched["id"]


def test_resolve_or_create_fuzzy_disambiguation_returns_different():
    entities_store.create_entity("person", "Jane Doe")

    def disambiguate(_candidate, _name, _score):
        return False  # different person

    e = entities_store.resolve_or_create("Jan Doe", "person", disambiguate_fn=disambiguate)
    # New entity created.
    all_jds = [
        x for x in entities_store.list_entities(kind="person")
        if x["canonical_name"] in ("Jane Doe", "Jan Doe")
    ]
    assert len(all_jds) == 2


def test_resolve_or_create_rejects_unknown_kind():
    with pytest.raises(ValueError):
        entities_store.resolve_or_create("X", "banana")


def test_add_alias_dedupes():
    e = entities_store.create_entity("person", "Jason")
    entities_store.add_alias(e["id"], "Jason")  # same as canonical
    entities_store.add_alias(e["id"], "JW")
    entities_store.add_alias(e["id"], "jw")  # case insensitive dedup
    e2 = entities_store.get_entity(e["id"])
    aliases = json.loads(e2["aliases_json"])
    assert aliases == ["JW"]


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------


def test_add_mention_increments_count_and_last_seen():
    e = entities_store.create_entity("person", "Sara")
    entities_store.add_mention(
        e["id"], "segment", "rec1:5",
        recording_id="rec1", timestamp=10.0, speaker="Speaker 1",
        snippet="Sara joined the call",
    )
    e2 = entities_store.get_entity(e["id"])
    assert e2["mention_count"] == 1
    assert e2["last_seen_at"] >= e["last_seen_at"]


def test_list_mentions_filter_by_source_type():
    e = entities_store.create_entity("person", "Sara")
    entities_store.add_mention(e["id"], "segment", "rec1:1", recording_id="rec1")
    entities_store.add_mention(e["id"], "outcome", "rec1", recording_id="rec1")
    assert len(entities_store.list_mentions(e["id"])) == 2
    assert len(entities_store.list_mentions(e["id"], source_types=["segment"])) == 1


def test_recent_activity_view_includes_recording_title():
    storage.create_job("rec-act", "/tmp/x.wav", "weekly-sync.wav")
    e = entities_store.create_entity("person", "Jamal")
    entities_store.add_mention(
        e["id"], "segment", "rec-act:0",
        recording_id="rec-act", timestamp=4.0, snippet="..."
    )
    rows = entities_store.list_recent_activity_by_entity(e["id"])
    assert len(rows) == 1
    assert rows[0]["recording_title"] == "weekly-sync.wav"


def test_delete_mentions_for_recording():
    e = entities_store.create_entity("person", "Sara")
    entities_store.add_mention(e["id"], "segment", "r:0", recording_id="r")
    entities_store.add_mention(e["id"], "segment", "r:1", recording_id="r")
    n = entities_store.delete_mentions_for_recording("r")
    assert n == 2


# ---------------------------------------------------------------------------
# FTS triggers
# ---------------------------------------------------------------------------


def test_segments_fts_populated_via_trigger():
    storage.create_job("rec-fts", "/tmp/x.wav", "x.wav")
    storage.update_job(
        "rec-fts",
        result={
            "segments": [
                {"start": 0, "end": 1, "speaker": "S1", "text": "We talked about pricing."},
                {"start": 1, "end": 2, "speaker": "S2", "text": "$400 quotation."},
            ]
        },
    )
    conn = storage._get_conn()
    rows = conn.execute(
        "SELECT recording_id, text FROM segments_fts WHERE segments_fts MATCH 'pricing'"
    ).fetchall()
    assert len(rows) == 1
    rows = conn.execute(
        "SELECT recording_id, text FROM segments_fts WHERE segments_fts MATCH 'quotation'"
    ).fetchall()
    assert len(rows) == 1


def test_segments_fts_handles_replacement_via_delete_trigger():
    storage.create_job("rec-fts2", "/tmp/x.wav", "x.wav")
    storage.update_job(
        "rec-fts2",
        result={"segments": [{"start": 0, "end": 1, "speaker": "S1", "text": "first text"}]},
    )
    storage.update_job(
        "rec-fts2",
        result={"segments": [{"start": 0, "end": 1, "speaker": "S1", "text": "second text"}]},
    )
    conn = storage._get_conn()
    rows = conn.execute(
        "SELECT text FROM segments_fts WHERE segments_fts MATCH 'first'"
    ).fetchall()
    assert rows == []
    rows = conn.execute(
        "SELECT text FROM segments_fts WHERE segments_fts MATCH 'second'"
    ).fetchall()
    assert len(rows) == 1


def test_attachments_fts_populated_via_trigger():
    storage.create_attachment(
        attachment_id="att1",
        recording_id="rec-att",
        filename="design.pdf",
        file_type="pdf",
        file_size=1234,
        extracted_text="The auth spec references OAuth flows.",
    )
    conn = storage._get_conn()
    rows = conn.execute(
        "SELECT filename FROM attachments_fts WHERE attachments_fts MATCH 'oauth'"
    ).fetchall()
    assert len(rows) == 1


def test_outcomes_indexed_via_helper():
    entities_store.index_outcomes(
        "rec-out",
        [
            {"id": "o1", "type": "decision", "title": "Adopt Postgres", "detail": "..."},
            {"id": "o2", "type": "blocker", "title": "Vendor delay", "detail": "Acme is slow."},
        ],
    )
    conn = storage._get_conn()
    rows = conn.execute(
        "SELECT outcome_id FROM outcomes_fts WHERE outcomes_fts MATCH 'postgres'"
    ).fetchall()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def test_deterministic_pre_pass_finds_money():
    segs = [
        {"text": "We agreed on $400 for the quote.", "speaker": "S1"},
        {"text": "Other budget items.", "speaker": "S2"},
    ]
    mentions = deterministic_pre_pass(segs)
    assert len(mentions) == 1
    assert mentions[0]["kind"] == "money"
    assert "$400" in mentions[0]["name"]
    assert mentions[0]["segment_index"] == 0


def test_run_entitize_uses_pre_pass_when_llm_absent():
    storage.create_job("rec-ent", "/tmp/x.wav", "x.wav")
    storage.update_job(
        "rec-ent",
        status="completed",
        extraction_status="completed",
        result={
            "segments": [
                {"start": 0, "end": 2, "speaker": "John", "text": "Quote came in at $400."},
            ]
        },
        outcomes=[{"id": "o1", "type": "decision", "title": "Approve quote", "detail": ""}],
    )
    app_state = SimpleNamespace(llm=None, ghost_llm=None)
    stats = run_entitize("rec-ent", app_state)
    assert stats["mentions_written"] == 1
    mentions = entities_store.list_mentions(
        entities_store.list_entities(kind="money")[0]["id"]
    )
    assert mentions[0]["recording_id"] == "rec-ent"
    assert mentions[0]["timestamp"] == 0.0


def test_run_entitize_idempotent_on_rerun():
    storage.create_job("rec-idem", "/tmp/x.wav", "x.wav")
    storage.update_job(
        "rec-idem",
        status="completed",
        extraction_status="completed",
        result={"segments": [{"start": 0, "end": 1, "speaker": "S1", "text": "Quote: $400"}]},
        outcomes=[],
    )
    app_state = SimpleNamespace(llm=None, ghost_llm=None)
    run_entitize("rec-idem", app_state)
    run_entitize("rec-idem", app_state)
    # Should be exactly one mention even after two runs.
    money_entity = entities_store.list_entities(kind="money")[0]
    assert money_entity["mention_count"] == 1


def test_run_entitize_with_fake_llm_merges_with_deterministic():
    storage.create_job("rec-llm", "/tmp/x.wav", "x.wav")
    storage.update_job(
        "rec-llm",
        status="completed",
        extraction_status="completed",
        result={
            "segments": [
                {"start": 0, "end": 1, "speaker": "S1", "text": "Jason proposed $400 budget."},
            ]
        },
        outcomes=[],
    )

    class FakeLLM:
        def create_chat_completion(self, **kwargs):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "mentions": [
                                        {
                                            "name": "Jason",
                                            "kind": "person",
                                            "canonical_name": "Jason",
                                            "aliases": [],
                                            "segment_index": 0,
                                            "snippet": "Jason proposed $400 budget.",
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }

    app_state = SimpleNamespace(llm=None, ghost_llm=FakeLLM())
    stats = run_entitize("rec-llm", app_state)
    # 1 money (deterministic) + 1 person (LLM)
    assert stats["mentions_written"] == 2
    kinds = {e["kind"] for e in entities_store.list_entities()}
    assert {"person", "money"}.issubset(kinds)


def test_backfill_all_recordings():
    storage.create_job("rec-bf1", "/tmp/x.wav", "x.wav")
    storage.update_job(
        "rec-bf1",
        status="completed",
        extraction_status="completed",
        result={"segments": [{"start": 0, "end": 1, "text": "Budget: $1,500"}]},
        outcomes=[],
    )
    storage.create_job("rec-bf2", "/tmp/y.wav", "y.wav")
    storage.update_job(
        "rec-bf2",
        status="completed",
        extraction_status="completed",
        result={"segments": [{"start": 0, "end": 1, "text": "We saw $2,000 last week"}]},
        outcomes=[],
    )
    app_state = SimpleNamespace(llm=None, ghost_llm=None)
    totals = backfill_all_recordings(app_state)
    assert totals["recordings_processed"] == 2
    assert totals["mentions_written"] >= 2


def test_index_outcomes_replaces_old():
    entities_store.index_outcomes(
        "rec-replace",
        [{"id": "o1", "type": "decision", "title": "Old", "detail": ""}],
    )
    entities_store.index_outcomes(
        "rec-replace",
        [{"id": "o2", "type": "decision", "title": "New", "detail": ""}],
    )
    conn = storage._get_conn()
    rows = conn.execute(
        "SELECT title FROM outcomes_fts WHERE recording_id = ?", ("rec-replace",)
    ).fetchall()
    titles = [r[0] for r in rows]
    assert titles == ["New"]
