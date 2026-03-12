"""In-memory job state store."""

from typing import Any

# In-memory store keyed by job_id
jobs: dict[str, dict[str, Any]] = {}


def create_job(job_id: str, file_path: str, original_filename: str) -> dict[str, Any]:
    """Create a new job with status='pending'."""
    job = {
        "id": job_id,
        "file_path": file_path,
        "original_filename": original_filename,
        "status": "pending",
        "result": None,
        "error": None,
        "extraction_status": "none",
        "extraction_error": None,
        "outcomes": [],
    }
    jobs[job_id] = job
    return job


def update_job(job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Update job fields."""
    if job_id not in jobs:
        raise KeyError(f"Job {job_id} not found")
    jobs[job_id].update(kwargs)
    return jobs[job_id]


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return job or None."""
    return jobs.get(job_id)
