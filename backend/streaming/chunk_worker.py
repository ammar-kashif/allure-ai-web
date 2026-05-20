"""Per-chunk processor: STT + VAD-aware embedding extraction.

Runs concurrently with the meeting recording. Each chunk is processed
independently; diarization clustering happens at finalize time over the
pooled embeddings (see finalizer.py).

Persistence model:
    chunk_progress row is the durable record. On entry we flip 'queued' ->
    'processing'; on success we write stt_segments_json + embeddings_path
    and flip to 'done'. The trigger on chunk_progress.state then bumps
    aggregate counters on recording_pipeline_state.

Idempotency: the worker is safe to call twice on the same chunk -- if the
row is already 'done' it short-circuits without touching the audio.
"""

import hashlib
import json
import logging
import os
from typing import Any, Optional

import numpy as np

from observability import log_event, step_timer
from streaming import progress_store

logger = logging.getLogger(__name__)

# Where per-chunk embeddings get persisted as .npy files. Lives alongside
# the chunks directory so cleanup is one rm -rf.
CHUNK_EMBEDDINGS_SUBDIR = "chunk_embeddings"


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _embeddings_dir(chunk_path: str) -> str:
    """Sibling directory for the chunk's audio file."""
    chunks_dir = os.path.dirname(chunk_path)
    parent = os.path.dirname(chunks_dir)
    out = os.path.join(parent, CHUNK_EMBEDDINGS_SUBDIR)
    os.makedirs(out, exist_ok=True)
    return out


def transcribe_chunk(chunk_path: str, transcriber) -> list[dict[str, Any]]:
    """STT over one chunk audio file. Returns segments in CHUNK-LOCAL time."""
    from transcription import transcribe_audio

    return transcribe_audio(chunk_path, transcriber)


def process_chunk(
    recording_id: str,
    chunk_seq: int,
    chunk_path: str,
    app_state: object,
    *,
    pipeline_version: int = 1,
    chunk_offset_seconds: float = 0.0,
) -> dict[str, Any]:
    """Run STT + embedding extraction on a single chunk and persist results.

    `chunk_offset_seconds` is the meeting-global start time of this chunk's
    first sample. Used to translate chunk-local timestamps into meeting-global
    timestamps for the finalize step.

    Returns the updated chunk_progress row.
    """
    # Idempotency check: if this chunk is already done at this version, no-op.
    existing = progress_store.get_chunk(recording_id, chunk_seq, pipeline_version)
    if existing and existing["state"] == "done":
        logger.info(
            "chunk already done: recording=%s seq=%d v=%d -- skipping",
            recording_id, chunk_seq, pipeline_version,
        )
        return existing

    sha = compute_sha256(chunk_path)
    progress_store.ensure_recording(recording_id, stage="streaming")
    row = progress_store.upsert_chunk(
        recording_id=recording_id,
        chunk_seq=chunk_seq,
        chunk_path=chunk_path,
        sha256=sha,
        pipeline_version=pipeline_version,
        seconds_start=chunk_offset_seconds,
    )

    # If the row already reflects a completed run for the same sha, short-circuit.
    if row["state"] == "done":
        return row

    progress_store.update_chunk(
        recording_id, chunk_seq, pipeline_version, state="processing"
    )

    log_event(
        category="streaming",
        event="chunk.start",
        status="start",
        message=f"Processing chunk {chunk_seq}",
        recording_id=recording_id,
        metadata={"chunk_path": chunk_path, "sha": sha[:12]},
    )

    try:
        with step_timer(
            "streaming.chunk_stt",
            category="streaming",
            recording_id=recording_id,
            chunk_seq=chunk_seq,
        ):
            stt_segments = transcribe_chunk(chunk_path, app_state.transcriber)

        with step_timer(
            "streaming.chunk_embeddings",
            category="streaming",
            recording_id=recording_id,
            chunk_seq=chunk_seq,
        ):
            window_payload = app_state.diarizer.extract_chunk_embeddings(chunk_path)

        # Persist embeddings to a sidecar .npy.
        embeddings = window_payload["embeddings"]
        chunk_duration = float(window_payload["duration"])
        emb_dir = _embeddings_dir(chunk_path)
        emb_path = os.path.join(emb_dir, f"{recording_id}_{chunk_seq:06d}_v{pipeline_version}.npy")
        np.save(emb_path, embeddings)

        emb_meta = {
            "n_windows": int(embeddings.shape[0]) if embeddings.size else 0,
            "dim": int(embeddings.shape[1]) if embeddings.ndim == 2 and embeddings.size else 0,
            "starts": [float(s) for s in window_payload["starts"]],
            "ends": [float(e) for e in window_payload["ends"]],
            "chunk_duration": chunk_duration,
        }

        # Translate STT segment timestamps to chunk-local floats for storage;
        # the finalizer adds the chunk offset to get meeting-global time.
        chunk_stt_local = [
            {
                "start": float(s.get("start", 0.0)),
                "end": float(s.get("end", 0.0)),
                "text": s.get("text", ""),
                "confidence": float(s.get("confidence", 1.0)),
            }
            for s in stt_segments
        ]

        progress_store.update_chunk(
            recording_id,
            chunk_seq,
            pipeline_version,
            state="done",
            seconds_end=chunk_offset_seconds + chunk_duration,
            stt_segments_json=json.dumps(chunk_stt_local),
            embeddings_path=emb_path,
            embeddings_meta_json=json.dumps(emb_meta),
        )
        log_event(
            category="streaming",
            event="chunk.done",
            status="done",
            message=f"Chunk {chunk_seq} processed",
            recording_id=recording_id,
            metadata={
                "n_segments": len(chunk_stt_local),
                "n_windows": emb_meta["n_windows"],
                "duration_s": round(chunk_duration, 2),
            },
        )
        return progress_store.get_chunk(recording_id, chunk_seq, pipeline_version)  # type: ignore[return-value]
    except Exception as exc:
        logger.exception("chunk processing failed: %s seq=%d", recording_id, chunk_seq)
        try:
            progress_store.update_chunk(
                recording_id,
                chunk_seq,
                pipeline_version,
                state="failed",
                error=str(exc),
            )
        except KeyError:
            pass
        log_event(
            category="streaming",
            event="chunk.failed",
            status="failed",
            level="error",
            message=f"Chunk {chunk_seq} failed",
            recording_id=recording_id,
            metadata={"error": str(exc)},
        )
        raise


def load_chunk_embeddings(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Read a chunk's persisted embeddings back into memory. Returns None if
    the row doesn't carry embeddings (failed / not yet processed)."""
    emb_path = row.get("embeddings_path")
    meta_json = row.get("embeddings_meta_json")
    if not emb_path or not meta_json or not os.path.exists(emb_path):
        return None
    embeddings = np.load(emb_path)
    meta = json.loads(meta_json)
    return {
        "embeddings": embeddings,
        "starts": meta.get("starts", []),
        "ends": meta.get("ends", []),
        "chunk_duration": float(meta.get("chunk_duration", 0.0)),
    }
