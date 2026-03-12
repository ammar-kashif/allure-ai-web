"""Async job queue with sequential worker."""

import asyncio

from storage import get_job, update_job
from transcription import run_transcription

# Global async job queue
job_queue: asyncio.Queue[str] = asyncio.Queue()


async def process_worker(app_state: object) -> None:
    """Infinite loop worker that processes jobs sequentially."""
    while True:
        job_id = await job_queue.get()
        try:
            job = get_job(job_id)
            if job is None:
                continue

            update_job(job_id, status="processing")

            result = await asyncio.to_thread(run_transcription, job_id, app_state)

            update_job(job_id, status="completed", result=result)
        except Exception as exc:
            try:
                update_job(job_id, status="failed", error=str(exc))
            except KeyError:
                pass
        finally:
            job_queue.task_done()
