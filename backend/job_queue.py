"""Async job queues + workers.

Two queues:
    job_queue   -- sequential worker(s) for "stt", "extract", "finalize"
                   (LLM-bound; serializes behind the local Llama lock).
    chunk_queue -- multiple concurrent workers for "stt_chunk" (CPU,
                   shares the singleton Moonshine + ECAPA + VAD models).

`STT_CHUNK_CONCURRENCY` env var controls the chunk worker pool size
(default 2). The legacy `stt` job type still runs through `job_queue` for
whole-file uploads; the streaming pipeline uses `stt_chunk` + `finalize`.
"""

import asyncio
import logging
import os

from frontend_sync import push_metadata_to_frontend, rename_audio_files
from observability import log_event, step_timer
from storage import get_job, update_job
from transcription import run_transcription

logger = logging.getLogger(__name__)

# Global async job queue -- tuple of (job_id, job_type)
job_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

# Chunk queue carries (recording_id, chunk_seq, chunk_path, pipeline_version,
# chunk_offset_seconds) tuples. Multiple workers can drain it concurrently
# because the underlying STT + embedding extraction is CPU and the shared
# model singletons are inference-only.
chunk_queue: asyncio.Queue[tuple[str, int, str, int, float]] = asyncio.Queue()

STT_CHUNK_CONCURRENCY = int(os.environ.get("STT_CHUNK_CONCURRENCY", "2"))


async def process_worker(app_state: object) -> None:
    """Infinite loop worker that processes jobs sequentially.

    Handles two job types:
    - "stt": Run transcription, then auto-chain extraction
    - "extract": Run LLM extraction on completed transcript; persists
      meeting_title/meeting_description back to the job result so the
      frontend transcript route can sync them locally.
    """
    while True:
        job_id, job_type = await job_queue.get()
        try:
            job = get_job(job_id)
            if job is None:
                continue

            if job_type == "stt":
                update_job(job_id, status="processing")
                with step_timer("job.stt", job_id=job_id):
                    result = await asyncio.to_thread(
                        run_transcription, job_id, app_state
                    )
                # Atomic flip: status=completed AND extraction_status=pending in
                # a single update. Otherwise a frontend poll landing between the
                # two writes sees status=ready + extraction=none, treats it as
                # "settled", and STOPS polling — title never gets a refresh trigger.
                update_job(
                    job_id,
                    status="completed",
                    result=result,
                    extraction_status="pending",
                )
                log_event(
                    category="transcription",
                    event="stt.completed",
                    status="done",
                    message="Transcription pipeline completed",
                    job_id=job_id,
                )

                # Auto-chain extraction after STT
                await job_queue.put((job_id, "extract"))
                log_event(
                    category="extraction",
                    event="extraction.queued",
                    status="done",
                    message="Queued recording for outcome extraction",
                    job_id=job_id,
                )

            elif job_type == "finalize":
                # Streaming-pipeline counterpart to "stt": pools per-chunk
                # embeddings + STT, runs global diarization clustering,
                # writes the canonical transcript result, then chains into
                # extract just like "stt" does.
                from streaming.finalizer import finalize_recording

                with step_timer("job.finalize", job_id=job_id):
                    result = await asyncio.to_thread(
                        finalize_recording, job_id, app_state
                    )
                update_job(
                    job_id,
                    status="completed",
                    result=result,
                    extraction_status="pending",
                )
                log_event(
                    category="streaming",
                    event="finalize.completed",
                    status="done",
                    message="Streaming finalize completed",
                    job_id=job_id,
                )
                await job_queue.put((job_id, "extract"))
                log_event(
                    category="extraction",
                    event="extraction.queued",
                    status="done",
                    message="Queued recording for outcome extraction",
                    job_id=job_id,
                )

            elif job_type == "extract":
                update_job(job_id, extraction_status="processing")
                # Import inside branch to avoid circular imports
                from extraction import run_extraction

                with step_timer("job.extract", job_id=job_id):
                    extraction_result = await asyncio.to_thread(
                        run_extraction, job_id, app_state
                    )

                outcomes = extraction_result.get("outcomes", [])
                meeting_title = extraction_result.get("meeting_title", "")
                meeting_description = extraction_result.get("meeting_description", "")
                corrections_applied = extraction_result.get("corrections_applied", [])

                # Merge title/description/corrections back into the stored
                # transcript result. run_extraction already mutated segments
                # in place for any applied corrections.
                stored = get_job(job_id) or {}
                stored_result = stored.get("result") or {}
                if meeting_title:
                    stored_result["meeting_title"] = meeting_title
                if meeting_description:
                    stored_result["meeting_description"] = meeting_description
                if corrections_applied:
                    stored_result["corrections_applied"] = corrections_applied
                update_job(job_id, result=stored_result)

                # IMPORTANT ORDER: push title/description to the frontend DB
                # *before* flipping extraction_status to "completed". The
                # frontend's polling hook stops polling the moment it sees
                # extraction_status=completed, so the local DB must already
                # hold the new title by then — otherwise the page never gets
                # a refetch trigger and the placeholder lingers.
                try:
                    sync_result = await asyncio.to_thread(
                        push_metadata_to_frontend,
                        job_id,
                        meeting_title,
                        meeting_description,
                    )
                    logger.info(
                        "frontend sync for %s: %s", job_id, sync_result
                    )
                except Exception as sync_exc:  # noqa: BLE001
                    logger.warning(
                        "frontend metadata push failed for %s: %s",
                        job_id,
                        sync_exc,
                    )

                # Rename the audio files to use a slugified title — also before
                # the status flip so any audio fetches triggered by the refresh
                # resolve to the new paths.
                if meeting_title:
                    try:
                        latest_job = get_job(job_id) or {}
                        backend_wav = latest_job.get("file_path")
                        renamed = await asyncio.to_thread(
                            rename_audio_files,
                            job_id,
                            meeting_title,
                            backend_wav,
                        )
                        new_backend_wav = renamed.get("backend_wav")
                        if new_backend_wav and new_backend_wav != backend_wav:
                            update_job(job_id, file_path=new_backend_wav)
                            logger.info(
                                "Updated backend file_path for %s -> %s",
                                job_id,
                                new_backend_wav,
                            )
                    except Exception as rn_exc:  # noqa: BLE001
                        logger.warning(
                            "Audio rename failed for %s: %s", job_id, rn_exc
                        )

                # Frontend DB is now fully up to date — safe to flip the
                # extraction status. The next /status poll will see "completed"
                # and the hook will invalidate ["recording", id] / ["transcript", id]
                # which re-fetches with the title already in place.
                update_job(
                    job_id, extraction_status="completed", outcomes=outcomes
                )

                log_event(
                    category="extraction",
                    event="extraction.completed",
                    status="done",
                    message="Outcome extraction completed",
                    job_id=job_id,
                    metadata={"outcome_count": len(outcomes)},
                )

                # Chain entity extraction: populates entity_mentions used by
                # Ghost retrieval. Decoupled into its own queue item so a
                # failure here can't roll back the user-visible extraction
                # status.
                await job_queue.put((job_id, "entitize"))

            elif job_type == "entitize":
                from entities.extractor import run_entitize

                with step_timer("job.entitize", job_id=job_id):
                    stats = await asyncio.to_thread(
                        run_entitize, job_id, app_state
                    )
                log_event(
                    category="entitize",
                    event="entitize.completed",
                    status="done",
                    message="Entity extraction completed",
                    job_id=job_id,
                    metadata=stats,
                )

        except Exception as exc:
            logger.error("Job %s (%s) failed: %s", job_id, job_type, exc, exc_info=True)
            try:
                if job_type == "stt":
                    update_job(job_id, status="failed", error=str(exc))
                    log_event(
                        category="transcription",
                        event="stt.failed",
                        status="failed",
                        level="error",
                        message="Transcription pipeline failed",
                        job_id=job_id,
                        metadata={"error": str(exc)},
                    )
                else:
                    update_job(
                        job_id,
                        extraction_status="failed",
                        extraction_error=str(exc),
                    )
                    log_event(
                        category="extraction",
                        event="extraction.failed",
                        status="failed",
                        level="error",
                        message="Outcome extraction failed",
                        job_id=job_id,
                        metadata={"error": str(exc)},
                    )
            except KeyError:
                pass
        finally:
            job_queue.task_done()


async def chunk_worker_loop(app_state: object, worker_id: int = 0) -> None:
    """Pull stt_chunk jobs off the chunk_queue and process them.

    Concurrency-safe: each chunk row is keyed by (recording_id, chunk_seq,
    pipeline_version) in chunk_progress, and processing is idempotent
    (sha256 check, state machine). Multiple instances of this loop can run
    against the same app_state because the Moonshine + ECAPA + VAD models
    are inference-only singletons.
    """
    from streaming.chunk_worker import process_chunk

    logger.info("chunk worker %d started", worker_id)
    while True:
        item = await chunk_queue.get()
        recording_id, chunk_seq, chunk_path, pipeline_version, chunk_offset = item
        try:
            with step_timer(
                "job.stt_chunk",
                category="streaming",
                recording_id=recording_id,
                chunk_seq=chunk_seq,
                worker=worker_id,
            ):
                await asyncio.to_thread(
                    process_chunk,
                    recording_id,
                    chunk_seq,
                    chunk_path,
                    app_state,
                    pipeline_version=pipeline_version,
                    chunk_offset_seconds=chunk_offset,
                )
        except Exception as exc:
            logger.error(
                "chunk job failed: recording=%s seq=%d: %s",
                recording_id, chunk_seq, exc, exc_info=True,
            )
        finally:
            chunk_queue.task_done()


def start_chunk_worker_pool(app_state: object) -> list[asyncio.Task]:
    """Spawn STT_CHUNK_CONCURRENCY chunk workers. Stored on app_state for shutdown."""
    tasks: list[asyncio.Task] = []
    for i in range(max(1, STT_CHUNK_CONCURRENCY)):
        t = asyncio.create_task(
            chunk_worker_loop(app_state, worker_id=i),
            name=f"chunk-worker-{i}",
        )
        tasks.append(t)
    return tasks
