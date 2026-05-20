"""Autonomy job orchestrator.

Entry point called by `job_queue.process_worker` when a job of type
"autonomy" pops off the queue. Handles skip-condition checks, the
detect → verify → execute sequence, and run-row bookkeeping.

Never raises into the worker — failure marks the run as 'failed' and
swallows the exception. The downstream tasks list and the UI shouldn't
brick if one autonomy pass blows up.
"""

from __future__ import annotations

import logging
from typing import Any

from observability import log_event, step_timer
from storage import get_job

from . import store as autonomy_store
from .detector import build_context, run_detect
from .executor import apply
from .store import _now_iso

logger = logging.getLogger(__name__)

MIN_DURATION_SECONDS = 120.0


def _is_first_in_project(project_id: str, current_recording_id: str) -> bool:
    """True if no other completed jobs exist for this project."""
    import sqlite3 as _sqlite3

    import storage

    conn = storage._get_conn()
    conn.row_factory = _sqlite3.Row
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM jobs "
        "WHERE project_id = ? AND id != ? AND extraction_status = 'completed'",
        (project_id, current_recording_id),
    ).fetchone()
    conn.row_factory = None
    return int(row["n"] or 0) == 0


def _check_skip_conditions(job_id: str) -> tuple[bool, str | None, str | None]:
    """Returns (should_skip, skip_reason, project_id_or_None)."""
    job = get_job(job_id)
    if job is None:
        return True, "no_project", None
    project_id = job.get("project_id")
    result = job.get("result") or {}
    duration = float(result.get("duration") or 0.0)

    settings = autonomy_store.get_settings()
    if not settings["enabled"]:
        return True, "disabled_global", project_id
    if project_id is None:
        return True, "no_project", None
    if project_id in (settings["disabled_project_ids"] or []):
        return True, "disabled_project", project_id
    if duration < MIN_DURATION_SECONDS:
        return True, "too_short", project_id
    if _is_first_in_project(project_id, job_id):
        return True, "first_in_project", project_id
    spent = autonomy_store.month_to_date_cost_usd()
    if spent >= float(settings["monthly_cap_usd"] or 0):
        return True, "cap_reached", project_id
    return False, None, project_id


def run_autonomy(job_id: str, app_state: object) -> dict[str, Any]:
    """Top-level autonomy pass for one recording. Always returns a
    summary dict; never raises into the worker."""

    log_event(
        category="autonomy",
        event="autonomy.start",
        status="start",
        message="Autonomy pass starting",
        recording_id=job_id,
    )

    should_skip, skip_reason, project_id = _check_skip_conditions(job_id)
    if should_skip:
        run = autonomy_store.mark_skipped(job_id, project_id, skip_reason or "no_project")
        log_event(
            category="autonomy",
            event="autonomy.skipped",
            status="done",
            message=f"Skipped: {skip_reason}",
            recording_id=job_id,
            metadata={"run_id": run["id"], "skip_reason": skip_reason},
        )
        return {"run_id": run["id"], "status": "skipped", "skip_reason": skip_reason}

    run = autonomy_store.create_run(job_id, project_id, status="running")

    # Get an LLM. If hosted settings aren't configured, mark failed and
    # bail — autonomy needs a hosted LLM (no local path yet, same as Ghost).
    try:
        from ghost.llm import get_llm

        llm = get_llm()
    except Exception as exc:
        msg = str(exc)
        autonomy_store.update_run(
            run["id"],
            status="failed",
            error=msg,
            completed_at=_now_iso(),
        )
        log_event(
            category="autonomy",
            event="autonomy.failed",
            status="failed",
            level="error",
            message=f"LLM unavailable: {msg}",
            recording_id=job_id,
            metadata={"run_id": run["id"]},
        )
        return {"run_id": run["id"], "status": "failed", "error": msg}

    try:
        with step_timer("autonomy.context", recording_id=job_id):
            context = build_context(job_id)

        with step_timer("autonomy.detect", recording_id=job_id):
            detect = run_detect(context, llm)

        log_event(
            category="autonomy",
            event="autonomy.detect",
            status="done",
            message=(
                f"matches={len(detect['payload'].get('task_matches', []))} "
                f"proposed={len(detect['payload'].get('proposed_new_tasks', []))} "
                f"follow_up={len(detect['payload'].get('follow_up_to_recordings', []))}"
            ),
            recording_id=job_id,
            metadata={
                "run_id": run["id"],
                "tokens_in": detect["tokens_in"],
                "tokens_out": detect["tokens_out"],
                "cost_usd": detect["cost_usd"],
            },
        )

        with step_timer("autonomy.execute", recording_id=job_id):
            exec_stats = apply(
                run["id"],
                job_id,
                detect["payload"],
                context,
                llm,
            )

        total_cost = round(
            float(detect["cost_usd"]) + float(exec_stats.get("verify_cost_usd", 0.0)),
            6,
        )
        autonomy_store.update_run(
            run["id"],
            status="completed",
            detect_tokens_in=detect["tokens_in"],
            detect_tokens_out=detect["tokens_out"],
            verify_tokens_in=exec_stats.get("verify_tokens_in", 0),
            verify_tokens_out=exec_stats.get("verify_tokens_out", 0),
            cost_usd=total_cost,
            follow_up_to=detect["payload"].get("follow_up_to_recordings") or [],
            completed_at=_now_iso(),
        )
        final = autonomy_store.get_run(run["id"]) or {}
        log_event(
            category="autonomy",
            event="autonomy.completed",
            status="done",
            message=(
                f"created={final.get('tasks_created', 0)} "
                f"discussed={final.get('tasks_discussed', 0)}"
            ),
            recording_id=job_id,
            metadata={"run_id": run["id"], "cost_usd": total_cost},
        )
        return {"run_id": run["id"], "status": "completed", "cost_usd": total_cost}

    except Exception as exc:
        msg = str(exc)
        logger.exception("autonomy run %s failed", run["id"])
        autonomy_store.update_run(
            run["id"],
            status="failed",
            error=msg,
            completed_at=_now_iso(),
        )
        log_event(
            category="autonomy",
            event="autonomy.failed",
            status="failed",
            level="error",
            message=msg,
            recording_id=job_id,
            metadata={"run_id": run["id"]},
        )
        return {"run_id": run["id"], "status": "failed", "error": msg}
