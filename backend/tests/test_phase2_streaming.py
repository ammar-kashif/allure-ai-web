"""Phase 2: streaming chunk worker + finalizer + resume logic.

These tests stub Moonshine, the diarizer, and the LLM so they run on CI
without GPU. The contract under test is the orchestration: chunk_progress
state machine, idempotency, sha-based dedup, resume-after-crash, and the
finalize→extract chain.
"""

import json
import os
import struct
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

import projects_store
import segments_store
import storage
from meeting_bot import dispatch_store
from streaming import chunk_worker, finalizer, progress_store, resume


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def init_phase2(reset_state):
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    progress_store.init()


@pytest.fixture
def minimal_wav(tmp_path):
    """Produce a tiny valid WAV (1s silence) for chunk processing."""
    num_samples = 16000
    sr = 16000
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ",
        16, 1, 1, sr, sr * 2, 2, 16, b"data", data_size,
    )
    p = tmp_path / "000001.mp3"
    with open(p, "wb") as f:
        f.write(header)
        f.write(b"\x00\x00" * num_samples)
    return str(p)


@pytest.fixture
def fake_app_state():
    """Stub transcriber + diarizer that produce deterministic outputs."""
    transcriber = MagicMock()
    # Moonshine result objects have .lines with .text/.start_time/.duration

    class FakeLine:
        def __init__(self, text, start_time, duration):
            self.text = text
            self.start_time = start_time
            self.duration = duration

    class FakeResult:
        def __init__(self, lines):
            self.lines = lines

    transcriber.transcribe_without_streaming.return_value = FakeResult(
        [FakeLine("Hello.", 0.0, 0.5), FakeLine("World.", 0.5, 0.5)]
    )

    diarizer = SimpleNamespace()

    def fake_extract(audio_path):
        # 2 windows of 192-dim embeddings.
        return {
            "embeddings": np.random.rand(2, 192).astype(np.float32),
            "starts": [0.0, 0.5],
            "ends": [0.5, 1.0],
            "duration": 1.0,
        }

    def fake_cluster(embs, starts, ends, total_duration):
        # All in one cluster.
        return [{"start": 0.0, "end": round(total_duration, 3), "speaker": "cluster_0"}]

    diarizer.extract_chunk_embeddings = fake_extract
    diarizer.cluster_pooled_embeddings = fake_cluster

    # No LLM = use default-role path.
    return SimpleNamespace(transcriber=transcriber, diarizer=diarizer, llm=None, punctuator=None)


# ---------------------------------------------------------------------------
# chunk_worker
# ---------------------------------------------------------------------------


def test_compute_sha256_stable(tmp_path):
    p = tmp_path / "x.mp3"
    p.write_bytes(b"\x00\x01\x02")
    a = chunk_worker.compute_sha256(str(p))
    b = chunk_worker.compute_sha256(str(p))
    assert a == b
    assert len(a) == 64


def test_moonshine_module_import_is_optional(minimal_wav, fake_app_state):
    """The chunk worker should call into transcription.transcribe_audio, which
    in turn imports moonshine_voice. Our fake transcriber bypasses both — this
    test ensures process_chunk doesn't require the real moonshine_voice module.
    """
    process_chunk = chunk_worker.process_chunk
    row = process_chunk(
        recording_id="rec1",
        chunk_seq=1,
        chunk_path=minimal_wav,
        app_state=fake_app_state,
        pipeline_version=1,
        chunk_offset_seconds=0.0,
    )
    assert row["state"] == "done"
    segs = json.loads(row["stt_segments_json"])
    assert len(segs) == 2
    assert segs[0]["text"] == "Hello."


def test_process_chunk_idempotent_when_already_done(minimal_wav, fake_app_state):
    chunk_worker.process_chunk(
        "rec-idem", 1, minimal_wav, fake_app_state, pipeline_version=1
    )
    # Second call should short-circuit without raising or duplicating rows.
    row = chunk_worker.process_chunk(
        "rec-idem", 1, minimal_wav, fake_app_state, pipeline_version=1
    )
    assert row["state"] == "done"
    chunks = progress_store.list_chunks_for_recording("rec-idem")
    assert len(chunks) == 1


def test_process_chunk_marks_failed_on_exception(minimal_wav, fake_app_state):
    fake_app_state.transcriber.transcribe_without_streaming.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        chunk_worker.process_chunk("rec-fail", 1, minimal_wav, fake_app_state)
    row = progress_store.get_chunk("rec-fail", 1, 1)
    assert row["state"] == "failed"
    assert "boom" in (row["error"] or "")


def test_chunk_done_bumps_aggregate_counter(minimal_wav, fake_app_state):
    chunk_worker.process_chunk("rec-count", 1, minimal_wav, fake_app_state)
    state = progress_store.get_state("rec-count")
    assert state["chunks_total"] == 1
    assert state["chunks_done"] == 1


def test_embeddings_persisted_as_npy(minimal_wav, fake_app_state):
    row = chunk_worker.process_chunk("rec-emb", 1, minimal_wav, fake_app_state)
    emb_path = row["embeddings_path"]
    assert emb_path and os.path.exists(emb_path)
    embs = np.load(emb_path)
    assert embs.shape == (2, 192)


def test_load_chunk_embeddings_returns_meta(minimal_wav, fake_app_state):
    row = chunk_worker.process_chunk("rec-load", 1, minimal_wav, fake_app_state)
    loaded = chunk_worker.load_chunk_embeddings(row)
    assert loaded is not None
    assert loaded["embeddings"].shape == (2, 192)
    assert loaded["starts"] == [0.0, 0.5]
    assert loaded["chunk_duration"] == 1.0


def test_load_chunk_embeddings_handles_missing_file(minimal_wav, fake_app_state):
    row = chunk_worker.process_chunk("rec-miss", 1, minimal_wav, fake_app_state)
    os.remove(row["embeddings_path"])
    assert chunk_worker.load_chunk_embeddings(row) is None


# ---------------------------------------------------------------------------
# finalizer
# ---------------------------------------------------------------------------


def test_finalize_assembles_transcript(minimal_wav, fake_app_state):
    # Create a job row so finalize can attach to it.
    storage.create_job("rec-final", minimal_wav, "test.wav")
    chunk_worker.process_chunk("rec-final", 1, minimal_wav, fake_app_state)
    progress_store.update_state("rec-final", stage="awaiting_finalize")
    result = finalizer.finalize_recording("rec-final", fake_app_state)
    assert "segments" in result
    assert "speakers" in result
    assert result["duration"] >= 1.0  # at least the one chunk
    state = progress_store.get_state("rec-final")
    assert state["stage"] == "finalized"


def test_finalize_writes_to_jobs_result(minimal_wav, fake_app_state):
    storage.create_job("rec-jr", minimal_wav, "test.wav")
    chunk_worker.process_chunk("rec-jr", 1, minimal_wav, fake_app_state)
    progress_store.update_state("rec-jr", stage="awaiting_finalize")
    finalizer.finalize_recording("rec-jr", fake_app_state)
    job = storage.get_job("rec-jr")
    assert job["status"] == "completed"
    assert job["result"]["segments"]


def test_finalize_skips_failed_chunks(minimal_wav, fake_app_state, tmp_path):
    storage.create_job("rec-skip", minimal_wav, "test.wav")
    # Chunk 1 succeeds; chunk 2 is manually marked failed.
    chunk_worker.process_chunk("rec-skip", 1, minimal_wav, fake_app_state)
    p2 = tmp_path / "000002.mp3"
    p2.write_bytes(b"\x00")
    progress_store.upsert_chunk("rec-skip", 2, str(p2), sha256="fail")
    progress_store.update_chunk("rec-skip", 2, state="failed", error="manual")
    result = finalizer.finalize_recording("rec-skip", fake_app_state)
    # Still produces a valid transcript from chunk 1.
    assert result["segments"]


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


def test_discover_new_chunks_skips_highest_by_default(tmp_path):
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    for n in (1, 2, 3):
        (chunks_dir / f"{n:06d}.mp3").write_bytes(b"x")
    new_rows = resume.discover_new_chunks("rec-x", str(chunks_dir), pipeline_version=1)
    seqs = sorted(r["chunk_seq"] for r in new_rows)
    assert seqs == [1, 2]  # 3 was held back


def test_discover_new_chunks_ignores_existing_rows(tmp_path):
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    (chunks_dir / "000001.mp3").write_bytes(b"x")
    (chunks_dir / "000002.mp3").write_bytes(b"x")
    progress_store.ensure_recording("rec-existing")
    progress_store.upsert_chunk(
        "rec-existing", 1, str(chunks_dir / "000001.mp3"), sha256="s1"
    )
    new_rows = resume.discover_new_chunks(
        "rec-existing", str(chunks_dir), pipeline_version=1, skip_highest_seq=False
    )
    seqs = sorted(r["chunk_seq"] for r in new_rows)
    assert seqs == [2]  # already had 1


def test_resume_unfinished_enqueues_pending_chunks(tmp_path):
    chunks_root = tmp_path / "recordings"
    rid_dir = chunks_root / "rec-resume" / "chunks"
    rid_dir.mkdir(parents=True)
    (rid_dir / "000001.mp3").write_bytes(b"x")
    (rid_dir / "000002.mp3").write_bytes(b"x")
    progress_store.ensure_recording("rec-resume", stage="awaiting_finalize")
    # Mark one chunk pre-existing and done.
    progress_store.upsert_chunk(
        "rec-resume", 1, str(rid_dir / "000001.mp3"), sha256="done-sha"
    )
    progress_store.update_chunk("rec-resume", 1, state="done")
    actions = resume.resume_unfinished(str(chunks_root))
    # awaiting_finalize disables skip_highest_seq, so we should see chunk 2
    # newly discovered, then queued for enqueue.
    enqueued = [a for a in actions if a["action"] == "enqueue_chunk"]
    assert any(a["chunk_seq"] == 2 for a in enqueued)


def test_resume_triggers_finalize_when_chunks_done(tmp_path, minimal_wav, fake_app_state):
    chunks_root = tmp_path / "recordings"
    rid_dir = chunks_root / "rec-fin" / "chunks"
    rid_dir.mkdir(parents=True)
    (rid_dir / "000001.mp3").write_bytes(b"x")
    chunk_worker.process_chunk("rec-fin", 1, minimal_wav, fake_app_state)
    progress_store.update_state("rec-fin", stage="awaiting_finalize")
    actions = resume.resume_unfinished(str(chunks_root))
    assert any(a["action"] == "enqueue_finalize" and a["recording_id"] == "rec-fin"
               for a in actions)


def test_pipeline_version_bump_isolates_old_runs(minimal_wav, fake_app_state):
    chunk_worker.process_chunk("rec-bump", 1, minimal_wav, fake_app_state)
    progress_store.bump_pipeline_version("rec-bump")
    state = progress_store.get_state("rec-bump")
    assert state["pipeline_version"] == 2
    # Old run still queryable for audit
    v1 = progress_store.list_chunks_for_recording("rec-bump", pipeline_version=1)
    v2 = progress_store.list_chunks_for_recording("rec-bump", pipeline_version=2)
    assert len(v1) == 1
    assert v2 == []
