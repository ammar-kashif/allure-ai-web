"""Async job queue with sequential worker supporting STT and extraction chaining."""

import asyncio
import logging

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
