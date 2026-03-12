"""Async job queue with sequential worker."""

import asyncio
import time

from storage import get_job, update_job

# Global async job queue
job_queue: asyncio.Queue[str] = asyncio.Queue()


def run_transcription(job_id: str, app_state: object) -> dict:
    """Run transcription for a job.

    STUB: Sleeps 1 second and returns empty result.
    Plan 02 replaces this with real Moonshine + pyannote logic.
    """
    time.sleep(1)
    return {
        "segments": [],
        "speakers": [],
        "duration": 0.0,
        "language": "en",
    }


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
