"""End-of-meeting finalize: pool per-chunk artifacts, run global diarization
clustering, assemble the canonical transcript, and stash it back into the
job row so the existing extraction pipeline can take over unchanged.

Why: chunks were processed independently; cluster IDs from chunk A do not
correspond to cluster IDs in chunk B. We pool embeddings, cluster once,
align each transcript segment to the global speaker labels, and from there
the rest of the pipeline (punctuate / snap / merge / stats / extract) is
identical to the offline path in `transcription.run_transcription`.
"""

import json
import logging
import time
from typing import Any

import numpy as np

from observability import log_event, step_timer
from segments_store import mirror_from_job_result
from storage import get_job, update_job
from streaming import chunk_worker, progress_store

logger = logging.getLogger(__name__)


def _pool_chunks(
    rows: list[dict[str, Any]]
) -> tuple[np.ndarray, list[float], list[float], list[dict[str, Any]], float]:
    """Walk done chunks (ordered by seq) and aggregate:
        - embeddings (translated to meeting-global timeline)
        - per-window starts/ends (meeting-global seconds)
        - transcript segments (meeting-global seconds)
        - total meeting duration

    Chunks in any non-'done' state are skipped with a warning; finalize
    will still produce a transcript from what we have.
    """
    all_embs: list[np.ndarray] = []
    all_starts: list[float] = []
    all_ends: list[float] = []
    stt: list[dict[str, Any]] = []
    offset = 0.0
    for row in rows:
        if row["state"] != "done":
            logger.warning(
                "Skipping chunk %s seq=%d in state=%s during finalize",
                row["recording_id"], row["chunk_seq"], row["state"],
            )
            continue
        chunk_offset = float(row.get("seconds_start") or 0.0)
        loaded = chunk_worker.load_chunk_embeddings(row)
        if loaded is None:
            logger.warning(
                "Chunk %s seq=%d marked done but embeddings missing -- skipping",
                row["recording_id"], row["chunk_seq"],
            )
            continue
        if loaded["embeddings"].size:
            all_embs.append(loaded["embeddings"])
            all_starts.extend([chunk_offset + s for s in loaded["starts"]])
            all_ends.extend([chunk_offset + e for e in loaded["ends"]])
        # STT segments are stored chunk-local; translate to meeting-global.
        stt_json = row.get("stt_segments_json") or "[]"
        local_segs = json.loads(stt_json)
        for s in local_segs:
            stt.append(
                {
                    "start": chunk_offset + float(s.get("start", 0.0)),
                    "end": chunk_offset + float(s.get("end", 0.0)),
                    "text": s.get("text", ""),
                    "confidence": float(s.get("confidence", 1.0)),
                }
            )
        # Track end-of-meeting as the latest chunk's end.
        offset = max(offset, float(row.get("seconds_end") or 0.0))

    if all_embs:
        pooled = np.concatenate(all_embs, axis=0)
    else:
        pooled = np.zeros((0, 192), dtype=np.float32)
    return pooled, all_starts, all_ends, stt, offset


def finalize_recording(
    recording_id: str,
    app_state: object,
    *,
    pipeline_version: int | None = None,
) -> dict[str, Any]:
    """Run global clustering + canonical transcript assembly. Persists the
    result back to the job row and returns it.

    Does not enqueue extraction -- the caller (worker) is responsible for
    that side-effect so the queue-level state machine stays explicit.
    """
    from transcription import (
        align_transcript_with_speakers,
        calculate_speaker_stats,
        identify_speakers_with_llm,
        merge_consecutive_segments,
        remap_speaker_labels,
        snap_boundaries_to_sentences,
        _assign_default_roles,
    )
    from text_post import punctuate_segments

    state = progress_store.get_state(recording_id)
    if state is None:
        raise ValueError(f"No pipeline state for recording {recording_id}")
    pv = pipeline_version or state["pipeline_version"]
    progress_store.update_state(recording_id, stage="finalizing")
    rows = progress_store.list_chunks_for_recording(recording_id, pipeline_version=pv)
    if not rows:
        raise ValueError(f"No chunks to finalize for {recording_id}")

    pipeline_start = time.perf_counter()

    with step_timer("streaming.finalize_pool", recording_id=recording_id):
        embeddings, starts, ends, stt_segments, total_duration = _pool_chunks(rows)

    logger.info(
        "Finalize pool for %s: %d embeddings, %d stt segments, duration=%.1fs",
        recording_id, embeddings.shape[0], len(stt_segments), total_duration,
    )

    with step_timer(
        "streaming.finalize_cluster",
        recording_id=recording_id,
        n_embeddings=int(embeddings.shape[0]),
    ):
        diarization_segments = app_state.diarizer.cluster_pooled_embeddings(
            embeddings, starts, ends, total_duration,
        )

    with step_timer("align", recording_id=recording_id):
        aligned = align_transcript_with_speakers(stt_segments, diarization_segments)

    punctuator = getattr(app_state, "punctuator", None)
    if punctuator is not None:
        aligned = punctuate_segments(aligned, punctuator)

    snapped = snap_boundaries_to_sentences(aligned)
    remapped = remap_speaker_labels(snapped)
    with step_timer("merge", recording_id=recording_id):
        merged = merge_consecutive_segments(remapped)
    with step_timer("stats", recording_id=recording_id):
        stats = calculate_speaker_stats(merged, total_duration)
    valid_speakers = {s["label"] for s in stats}
    filtered_segments = [s for s in merged if s["speaker"] in valid_speakers]

    if hasattr(app_state, "llm") and app_state.llm:
        with step_timer(
            "speaker_id.llm", recording_id=recording_id, n_speakers=len(stats)
        ):
            stats = identify_speakers_with_llm(filtered_segments, stats, app_state.llm)
    else:
        stats = _assign_default_roles(stats)

    processing_time = round(time.perf_counter() - pipeline_start, 2)
    result = {
        "id": recording_id,
        "duration": round(total_duration, 2),
        "language": "en",
        "speakers": stats,
        "segments": filtered_segments,
        "processing_time": processing_time,
    }

    # Persist back to the job row. update_job mirrors segments via the hook
    # added in Phase 1; we also call mirror_from_job_result here so the
    # mirror happens even if the job row didn't exist yet.
    job = get_job(recording_id)
    if job is not None:
        update_job(recording_id, status="completed", result=result)
    else:
        # Defensive: if a streaming-only recording was never written to jobs
        # (shouldn't happen in production), mirror anyway so retrieval has
        # something to query.
        mirror_from_job_result(recording_id, result)

    progress_store.update_state(recording_id, stage="finalized")
    log_event(
        category="streaming",
        event="finalize.done",
        status="done",
        message="Streaming finalize complete",
        recording_id=recording_id,
        metadata={
            "n_segments": len(filtered_segments),
            "n_speakers": len(stats),
            "duration_s": round(total_duration, 1),
            "processing_time_s": processing_time,
        },
    )
    return result
