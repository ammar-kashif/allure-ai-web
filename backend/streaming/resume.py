"""Resume in-flight streaming recordings on worker startup.

Walks recording_pipeline_state for any row not in `completed` / `failed`,
scans the chunks directory for any audio files not already represented in
chunk_progress, and re-enqueues whatever isn't yet `done`. Idempotent --
running it on every startup is safe.
"""

import logging
import os
from typing import Any

from observability import log_event
from streaming import progress_store

logger = logging.getLogger(__name__)


def chunks_dir_for(recordings_root: str, recording_id: str) -> str:
    return os.path.join(recordings_root, recording_id, "chunks")


def _seq_from_filename(name: str) -> int | None:
    """Filename pattern: '000001.mp3' / '000123.wav' -> 1 / 123."""
    base, _ = os.path.splitext(name)
    try:
        return int(base)
    except ValueError:
        return None


def discover_new_chunks(
    recording_id: str,
    chunks_dir: str,
    pipeline_version: int,
    *,
    skip_highest_seq: bool = True,
) -> list[dict[str, Any]]:
    """Walk chunks_dir, return rows representing chunks not yet in
    chunk_progress at this pipeline_version.

    `skip_highest_seq` excludes the highest-numbered file because ffmpeg's
    segmenter may still be writing it. The exception is when the recording
    has been finalized externally (caller can pass False).
    """
    if not os.path.isdir(chunks_dir):
        return []
    files: list[tuple[int, str]] = []
    for name in os.listdir(chunks_dir):
        if name.startswith("."):
            continue
        seq = _seq_from_filename(name)
        if seq is None:
            continue
        full = os.path.join(chunks_dir, name)
        if not os.path.isfile(full):
            continue
        files.append((seq, full))
    if not files:
        return []
    files.sort()
    if skip_highest_seq:
        files = files[:-1]
    new_rows: list[dict[str, Any]] = []
    for seq, path in files:
        existing = progress_store.get_chunk(recording_id, seq, pipeline_version)
        if existing is not None:
            continue
        new_rows.append({"chunk_seq": seq, "chunk_path": path})
    return new_rows


def list_chunks_to_enqueue(
    recording_id: str, pipeline_version: int
) -> list[dict[str, Any]]:
    """Chunks in `queued` or `processing` state at the current version.
    `processing` rows are re-enqueued because they could be partial.
    """
    all_rows = progress_store.list_chunks_for_recording(
        recording_id, pipeline_version=pipeline_version
    )
    return [r for r in all_rows if r["state"] in ("queued", "processing")]


def all_chunks_done(recording_id: str, pipeline_version: int) -> bool:
    rows = progress_store.list_chunks_for_recording(
        recording_id, pipeline_version=pipeline_version
    )
    if not rows:
        return False
    return all(r["state"] == "done" for r in rows)


def resume_unfinished(recordings_root: str) -> list[dict[str, Any]]:
    """Top-level resume scan. Returns a list of actions taken, mostly for
    logging / debugging. Caller is responsible for enqueueing the returned
    chunk rows into whatever queue they use.

    Returns list of dicts:
        {"action": "enqueue_chunk", "recording_id": ..., "chunk_seq": ..., "chunk_path": ...}
        {"action": "enqueue_finalize", "recording_id": ...}
    """
    actions: list[dict[str, Any]] = []
    for state in progress_store.list_unfinished_recordings():
        rid = state["recording_id"]
        pv = state["pipeline_version"]

        chunks_dir = chunks_dir_for(recordings_root, rid)
        new_rows = discover_new_chunks(
            rid, chunks_dir, pv,
            skip_highest_seq=state["stage"] not in ("awaiting_finalize",),
        )
        # Upsert new rows so the progress store knows about them.
        for nr in new_rows:
            # sha256 may be needed but we leave it for the worker; here we
            # only register the path with a placeholder so list_chunks_to_enqueue
            # can return it. The chunk worker will recompute sha on entry.
            try:
                progress_store.upsert_chunk(
                    rid,
                    nr["chunk_seq"],
                    nr["chunk_path"],
                    sha256=f"pending-{nr['chunk_seq']}",
                    pipeline_version=pv,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("upsert_chunk on resume failed for %s seq=%d: %s",
                               rid, nr["chunk_seq"], exc)

        to_run = list_chunks_to_enqueue(rid, pv)
        for row in to_run:
            actions.append({
                "action": "enqueue_chunk",
                "recording_id": rid,
                "chunk_seq": row["chunk_seq"],
                "chunk_path": row["chunk_path"],
                "pipeline_version": pv,
            })

        if state["stage"] == "awaiting_finalize" and not to_run and all_chunks_done(rid, pv):
            actions.append({"action": "enqueue_finalize", "recording_id": rid})

    if actions:
        log_event(
            category="streaming",
            event="resume.actions",
            status="done",
            message=f"Resume queued {len(actions)} action(s)",
            metadata={"counts": {
                "chunks": sum(1 for a in actions if a["action"] == "enqueue_chunk"),
                "finalize": sum(1 for a in actions if a["action"] == "enqueue_finalize"),
            }},
        )
    return actions
