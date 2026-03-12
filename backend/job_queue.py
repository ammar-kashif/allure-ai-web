"""Async job queue with sequential worker supporting STT and extraction chaining."""

import asyncio
import logging

from storage import get_job, update_job
from transcription import run_transcription

logger = logging.getLogger(__name__)

# Global async job queue -- tuple of (job_id, job_type)
job_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()


async def process_worker(app_state: object) -> None:
    """Infinite loop worker that processes jobs sequentially.

    Handles two job types:
    - "stt": Run transcription, then auto-chain extraction
    - "extract": Run LLM extraction on completed transcript
    """
    while True:
        job_id, job_type = await job_queue.get()
        try:
            job = get_job(job_id)
            if job is None:
                continue

            if job_type == "stt":
                update_job(job_id, status="processing")
                result = await asyncio.to_thread(
                    run_transcription, job_id, app_state
                )
                update_job(job_id, status="completed", result=result)

                # Auto-chain extraction after STT
                update_job(job_id, extraction_status="pending")
                await job_queue.put((job_id, "extract"))

            elif job_type == "extract":
                update_job(job_id, extraction_status="processing")
                # Import inside branch to avoid circular imports
                from extraction import run_extraction

                outcomes = await asyncio.to_thread(
                    run_extraction, job_id, app_state
                )
                update_job(
                    job_id, extraction_status="completed", outcomes=outcomes
                )

        except Exception as exc:
            logger.error("Job %s (%s) failed: %s", job_id, job_type, exc, exc_info=True)
            try:
                if job_type == "stt":
                    update_job(job_id, status="failed", error=str(exc))
                else:
                    update_job(
                        job_id,
                        extraction_status="failed",
                        extraction_error=str(exc),
                    )
            except KeyError:
                pass
        finally:
            job_queue.task_done()
