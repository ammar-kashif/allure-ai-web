"""Async job queue with sequential worker supporting STT, extraction, and chart chaining."""

import asyncio
import logging

from storage import get_job, update_job
from transcription import run_transcription

logger = logging.getLogger(__name__)

# Global async job queue -- tuple of (job_id, job_type)
job_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()


async def process_worker(app_state: object) -> None:
    """Infinite loop worker that processes jobs sequentially.

    Handles three job types:
    - "stt": Run transcription, run role inference, then auto-chain extraction
    - "extract": Run LLM extraction on completed transcript, then auto-chain chart
    - "chart": Generate PlantUML decision chart from extracted outcomes
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

                # Run role inference inline (non-fatal — failure must not block extraction)
                try:
                    from role_inference import run_role_inference
                    await asyncio.to_thread(run_role_inference, job_id, app_state)
                except Exception as role_exc:
                    logger.warning(
                        "Job %s: role inference failed (non-fatal): %s",
                        job_id,
                        role_exc,
                    )

                # Brief pause to allow concurrent document uploads to land before
                # extraction starts (document uploads happen in parallel from the
                # frontend after the audio POST returns).
                await asyncio.sleep(2)

                # Auto-chain extraction after STT
                update_job(job_id, extraction_status="pending")
                await job_queue.put((job_id, "extract"))

            elif job_type == "extract":
                update_job(job_id, extraction_status="processing")
                from extraction import run_extraction

                outcomes = await asyncio.to_thread(
                    run_extraction, job_id, app_state
                )
                update_job(
                    job_id, extraction_status="completed", outcomes=outcomes
                )

                # Auto-chain chart generation after extraction
                update_job(job_id, chart_status="pending")
                await job_queue.put((job_id, "chart"))

            elif job_type == "chart":
                update_job(job_id, chart_status="processing")
                from chart_generation import run_chart_generation

                plantuml = await asyncio.to_thread(
                    run_chart_generation, job_id, app_state
                )
                update_job(
                    job_id, chart_status="completed", chart_plantuml=plantuml
                )

        except Exception as exc:
            logger.error("Job %s (%s) failed: %s", job_id, job_type, exc, exc_info=True)
            try:
                if job_type == "stt":
                    update_job(job_id, status="failed", error=str(exc))
                elif job_type == "extract":
                    update_job(
                        job_id,
                        extraction_status="failed",
                        extraction_error=str(exc),
                    )
                elif job_type == "chart":
                    update_job(
                        job_id,
                        chart_status="failed",
                        chart_error=str(exc),
                    )
            except KeyError:
                pass
        finally:
            job_queue.task_done()
