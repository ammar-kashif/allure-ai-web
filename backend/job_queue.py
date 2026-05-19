"""Async job queue with sequential worker supporting STT and extraction chaining."""

import asyncio
import logging

from frontend_sync import push_metadata_to_frontend, rename_audio_files
from observability import log_event, step_timer
from storage import get_job, update_job
from transcription import run_transcription

logger = logging.getLogger(__name__)

# Global async job queue -- tuple of (job_id, job_type)
job_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()


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
                update_job(job_id, status="completed", result=result)
                log_event(
                    category="transcription",
                    event="stt.completed",
                    status="done",
                    message="Transcription pipeline completed",
                    job_id=job_id,
                )

                # Auto-chain extraction after STT
                update_job(job_id, extraction_status="pending")
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

                update_job(
                    job_id, extraction_status="completed", outcomes=outcomes
                )

                # PUSH to the frontend SQLite directly — don't wait for the
                # polling-based sync. The frontend's recordings row gets
                # title/description and its cached transcript blob is cleared
                # so the next page visit re-fetches the new content.
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

                # Rename the audio files to use a slugified title. Updates
                # backend's jobs.file_path and frontend's recordings.file_path
                # so subsequent /audio reads still resolve.
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

                log_event(
                    category="extraction",
                    event="extraction.completed",
                    status="done",
                    message="Outcome extraction completed",
                    job_id=job_id,
                    metadata={"outcome_count": len(outcomes)},
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
