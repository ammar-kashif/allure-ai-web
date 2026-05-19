"""Structured per-step pipeline timing logs.

Single source of truth for `step.start` / `step.done` / `step.failed` log lines.
A future Logs UI can route these through a DB writer alongside the logger.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("pipeline")


def _fmt(fields: dict[str, Any]) -> str:
    return " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)


def _category_for(step: str, fields: dict[str, Any]) -> str:
    explicit = fields.get("category")
    if isinstance(explicit, str) and explicit:
        return explicit
    if step.startswith("diarization"):
        return "diarization"
    if step.startswith("extraction") or "extract" in step:
        return "extraction"
    if step.startswith("document") or "prd" in step or "diagram" in step:
        return "document"
    if step.startswith("bot"):
        return "bot"
    if (
        step.startswith("stt")
        or step.startswith("job.stt")
        or step in {"align", "merge", "stats", "punctuate"}
        or step.startswith("speaker_id")
    ):
        return "transcription"
    return "pipeline"


def _ids_from(fields: dict[str, Any]) -> dict[str, str | None]:
    job_id = fields.get("job_id")
    recording_id = fields.get("recording_id")
    dispatch_id = fields.get("dispatch_id")
    return {
        "job_id": str(job_id) if job_id else None,
        "recording_id": str(recording_id) if recording_id else None,
        "dispatch_id": str(dispatch_id) if dispatch_id else None,
    }


def log_event(
    *,
    category: str,
    event: str,
    status: str,
    level: str = "info",
    message: str = "",
    recording_id: str | None = None,
    job_id: str | None = None,
    dispatch_id: str | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Best-effort structured event logging for the Logs page."""
    try:
        from log_store import record_event

        record_event(
            level=level,
            category=category,
            event=event,
            status=status,
            message=message,
            recording_id=recording_id,
            job_id=job_id,
            dispatch_id=dispatch_id,
            duration_ms=duration_ms,
            metadata=metadata,
        )
    except Exception as exc:
        logger.debug("structured log write skipped: %s", exc)


@contextmanager
def step_timer(step: str, **fields: Any) -> Iterator[None]:
    """Log start/done/failed for a named pipeline step with elapsed ms."""
    t0 = time.perf_counter()
    logger.info("step.start step=%s %s", step, _fmt(fields))
    ids = _ids_from(fields)
    category = _category_for(step, fields)
    metadata = {
        k: v
        for k, v in fields.items()
        if k not in {"category", "job_id", "recording_id", "dispatch_id"}
    }
    log_event(
        category=category,
        event=step,
        status="start",
        message=f"Started {step.replace('.', ' ')}",
        metadata=metadata,
        **ids,
    )
    try:
        yield
        dt_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("step.done step=%s dt_ms=%d %s", step, dt_ms, _fmt(fields))
        log_event(
            category=category,
            event=step,
            status="done",
            message=f"Completed {step.replace('.', ' ')}",
            duration_ms=dt_ms,
            metadata=metadata,
            **ids,
        )
    except Exception as e:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        logger.exception(
            "step.failed step=%s dt_ms=%d err=%r %s", step, dt_ms, e, _fmt(fields)
        )
        log_event(
            category=category,
            event=step,
            status="failed",
            level="error",
            message=f"Failed {step.replace('.', ' ')}",
            duration_ms=dt_ms,
            metadata={**metadata, "error": str(e)},
            **ids,
        )
        raise
