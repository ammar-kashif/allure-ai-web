"""Phase 1 foundation: projects, segments mirror, streaming progress store, metrics."""

import datetime as dt
import json

import pytest

import projects_store
import segments_store
import storage
from meeting_bot import dispatch_store
from metrics import pipeline_summary, step_latencies
from streaming import progress_store


@pytest.fixture(autouse=True)
def init_phase1(reset_state):
    """`reset_state` is autouse; this adds the Phase 1 inits on top."""
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    progress_store.init()


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------


def test_create_and_get_project():
    p = projects_store.create("Allure Web", description="primary product")
    assert p["name"] == "Allure Web"
    assert p["description"] == "primary product"
    assert p["archived_at"] is None
    fetched = projects_store.get(p["id"])
    assert fetched == p


def test_list_active_excludes_archived():
    p1 = projects_store.create("Active")
    p2 = projects_store.create("ToArchive")
    projects_store.archive(p2["id"])
    active = projects_store.list_active()
    ids = {x["id"] for x in active}
    assert p1["id"] in ids
    assert p2["id"] not in ids


def test_projects_backfilled_from_dispatches():
    # Existing project_id in dispatches must materialize a row on init().
    dispatch_store.create(
        recording_id="rec1",
        meeting_url="https://meet.google.com/abc",
        platform="google",
        project_id="proj-from-dispatch",
        title="standup",
    )
    # Re-run init to trigger backfill against the new dispatch row.
    projects_store.init()
    p = projects_store.get("proj-from-dispatch")
    assert p is not None
    assert p["name"] == "proj-from-dispatch"  # placeholder name


def test_jobs_get_project_id_column():
    cols = {row[1] for row in storage._get_conn().execute("PRAGMA table_info(jobs)").fetchall()}
    assert "project_id" in cols


def test_backfill_links_jobs_to_project():
    dispatch_store.create(
        recording_id="rec2",
        meeting_url="https://meet.google.com/xyz",
        platform="google",
        project_id="proj-x",
    )
    storage.create_job("rec2", "/tmp/x.wav", "x.wav")
    projects_store.init()  # re-run backfill
    job = storage.get_job("rec2")
    assert job["project_id"] == "proj-x"


# ---------------------------------------------------------------------------
# segments mirror
# ---------------------------------------------------------------------------


def test_segments_mirror_from_update_job():
    storage.create_job("job-seg", "/tmp/a.wav", "a.wav")
    result = {
        "duration": 12.0,
        "speakers": [],
        "segments": [
            {"start": 0.0, "end": 4.0, "speaker": "Speaker 1", "text": "Hello there.", "confidence": 0.97},
            {"start": 4.0, "end": 8.0, "speaker": "Speaker 2", "text": "Hi.", "confidence": 0.98},
        ],
    }
    storage.update_job("job-seg", status="completed", result=result)
    rows = segments_store.list_segments("job-seg")
    assert len(rows) == 2
    assert rows[0]["text"] == "Hello there."
    assert rows[0]["speaker"] == "Speaker 1"


def test_segments_mirror_replaces_on_update():
    storage.create_job("job-seg2", "/tmp/b.wav", "b.wav")
    storage.update_job(
        "job-seg2",
        result={"segments": [{"start": 0, "end": 1, "speaker": "A", "text": "first"}]},
    )
    storage.update_job(
        "job-seg2",
        result={"segments": [{"start": 0, "end": 1, "speaker": "B", "text": "second"}]},
    )
    rows = segments_store.list_segments("job-seg2")
    assert len(rows) == 1
    assert rows[0]["text"] == "second"


def test_segment_window_query():
    storage.create_job("job-win", "/tmp/c.wav", "c.wav")
    storage.update_job(
        "job-win",
        result={
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "a"},
                {"start": 2.0, "end": 4.0, "text": "b"},
                {"start": 4.0, "end": 6.0, "text": "c"},
                {"start": 6.0, "end": 8.0, "text": "d"},
            ]
        },
    )
    rows = segments_store.get_segment_window("job-win", 3.0, 5.0)
    # Overlap with [3,5]: segment idx 1 (2-4) and idx 2 (4-6)
    texts = [r["text"] for r in rows]
    assert texts == ["b", "c"]


def test_backfill_all_from_jobs():
    storage.create_job("job-bf", "/tmp/bf.wav", "bf.wav")
    # Write result directly via raw SQL to simulate a row that never went
    # through update_job (e.g. older data) -- the mirror should not have
    # populated automatically.
    conn = storage._get_conn()
    conn.execute(
        "UPDATE jobs SET status = ?, result = ? WHERE id = ?",
        ("completed", json.dumps({"segments": [{"start": 0, "end": 1, "text": "ghost"}]}), "job-bf"),
    )
    conn.commit()
    assert segments_store.list_segments("job-bf") == []
    n = segments_store.backfill_all_from_jobs()
    assert n == 1
    rows = segments_store.list_segments("job-bf")
    assert len(rows) == 1
    assert rows[0]["text"] == "ghost"


# ---------------------------------------------------------------------------
# streaming progress store
# ---------------------------------------------------------------------------


def test_ensure_recording_idempotent():
    s1 = progress_store.ensure_recording("rec-stream")
    s2 = progress_store.ensure_recording("rec-stream")
    assert s1["recording_id"] == s2["recording_id"] == "rec-stream"
    assert s1["pipeline_version"] == 1
    assert s1["stage"] == "streaming"


def test_upsert_chunk_and_state_progression():
    progress_store.ensure_recording("rec-a")
    c1 = progress_store.upsert_chunk(
        "rec-a", 1, "/tmp/000001.mp3", sha256="sha-001",
        seconds_start=0.0, seconds_end=30.0,
    )
    assert c1["state"] == "queued"
    state = progress_store.get_state("rec-a")
    assert state["chunks_total"] == 1  # insert trigger
    assert state["chunks_done"] == 0

    progress_store.update_chunk("rec-a", 1, state="processing")
    progress_store.update_chunk("rec-a", 1, state="done")
    state = progress_store.get_state("rec-a")
    assert state["chunks_done"] == 1
    assert pytest.approx(state["total_seconds"]) == 30.0


def test_upsert_chunk_idempotent_by_sha():
    progress_store.ensure_recording("rec-dup")
    progress_store.upsert_chunk("rec-dup", 1, "/tmp/x.mp3", sha256="dup-sha")
    progress_store.upsert_chunk("rec-dup", 1, "/tmp/x.mp3", sha256="dup-sha")
    progress_store.upsert_chunk("rec-dup", 99, "/tmp/x2.mp3", sha256="dup-sha")
    chunks = progress_store.list_chunks_for_recording("rec-dup")
    assert len(chunks) == 1
    assert chunks[0]["chunk_seq"] == 1


def test_bump_pipeline_version_resets_counters():
    progress_store.ensure_recording("rec-bump")
    progress_store.upsert_chunk("rec-bump", 1, "/tmp/a.mp3", sha256="s1", seconds_end=10.0)
    progress_store.update_chunk("rec-bump", 1, state="done")
    s = progress_store.get_state("rec-bump")
    assert s["chunks_done"] == 1
    assert s["pipeline_version"] == 1

    v = progress_store.bump_pipeline_version("rec-bump")
    assert v == 2
    s = progress_store.get_state("rec-bump")
    assert s["chunks_done"] == 0
    assert s["chunks_total"] == 0
    assert s["stage"] == "streaming"

    # Old version's rows are still there for audit.
    v1_chunks = progress_store.list_chunks_for_recording("rec-bump", pipeline_version=1)
    assert len(v1_chunks) == 1


def test_list_unfinished_excludes_completed_and_failed():
    progress_store.ensure_recording("rec-1")
    progress_store.ensure_recording("rec-2")
    progress_store.ensure_recording("rec-3")
    progress_store.update_state("rec-2", stage="completed")
    progress_store.update_state("rec-3", stage="failed")
    pending = progress_store.list_unfinished_recordings()
    ids = {r["recording_id"] for r in pending}
    assert ids == {"rec-1"}


def test_invalid_chunk_state_rejected():
    progress_store.ensure_recording("rec-bad")
    progress_store.upsert_chunk("rec-bad", 1, "/tmp/x.mp3", sha256="s")
    with pytest.raises(ValueError):
        progress_store.update_chunk("rec-bad", 1, state="banana")


def test_invalid_pipeline_stage_rejected():
    progress_store.ensure_recording("rec-bad2")
    with pytest.raises(ValueError):
        progress_store.update_state("rec-bad2", stage="banana")


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------


def test_step_latencies_aggregates_durations():
    from log_store import record_event

    record_event(
        level="info",
        category="transcription",
        event="stt.moonshine",
        status="done",
        duration_ms=1000,
    )
    record_event(
        level="info",
        category="transcription",
        event="stt.moonshine",
        status="done",
        duration_ms=2000,
    )
    record_event(
        level="info",
        category="transcription",
        event="stt.moonshine",
        status="done",
        duration_ms=4000,
    )
    rows = step_latencies()
    by_step = {(r["category"], r["event"]): r for r in rows}
    stt = by_step[("transcription", "stt.moonshine")]
    assert stt["count"] == 3
    assert stt["p50_ms"] == 2000
    assert stt["max_ms"] == 4000


def test_pipeline_summary_shape():
    from log_store import record_event

    record_event(
        level="info",
        category="extraction",
        event="extraction.llm",
        status="done",
        duration_ms=500,
    )
    summary = pipeline_summary()
    assert "steps" in summary
    assert "by_step" in summary
    assert "extraction.extraction.llm" in summary["by_step"]
