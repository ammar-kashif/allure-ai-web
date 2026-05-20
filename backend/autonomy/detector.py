"""Autonomy detector: build project context + one structured LLM call.

Ghost LLM exposes only `run_tool_use_loop` (no plain create_chat with
JSON-schema). To force structured output we register a single tool
whose `parameters` schema IS the detect output, and have the handler
capture the parsed arguments via a closure. The handler returns "ok"
so the LLM thinks the submission succeeded; on the next iteration it
naturally terminates because it has no other moves.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ghost.llm import LoopResult, estimate_cost_usd
from storage import get_job

from .prompts import DETECT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def list_same_project_recordings(
    project_id: str, exclude_recording_id: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Same-project completed jobs (newest first), excluding the current one."""
    import sqlite3 as _sqlite3

    import storage

    conn = storage._get_conn()
    conn.row_factory = _sqlite3.Row
    rows = conn.execute(
        "SELECT id, original_filename, result, outcomes FROM jobs "
        "WHERE project_id = ? AND extraction_status = 'completed' "
        "AND id != ? "
        "ORDER BY rowid DESC LIMIT ?",
        (project_id, exclude_recording_id, limit),
    ).fetchall()
    conn.row_factory = None
    out = []
    for r in rows:
        try:
            result = json.loads(r["result"]) if r["result"] else {}
        except Exception:
            result = {}
        try:
            outcomes = json.loads(r["outcomes"]) if r["outcomes"] else []
        except Exception:
            outcomes = []
        out.append({
            "id": r["id"],
            "filename": r["original_filename"],
            "meeting_title": result.get("meeting_title", ""),
            "outcomes": outcomes,
        })
    return out


def _truncate_segments(segments: list[dict[str, Any]], cap: int = 200) -> list[dict[str, Any]]:
    """Cap segments before formatting for the prompt to control token cost."""
    if len(segments) <= cap:
        return segments
    return segments[:cap]


def _format_transcript(segments: list[dict[str, Any]]) -> str:
    lines = []
    for i, seg in enumerate(segments):
        ts = float(seg.get("start", 0.0))
        m = int(ts) // 60
        s = int(ts) % 60
        speaker = seg.get("speaker", "?")
        text = (seg.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"[{i}] {m}:{s:02d} {speaker}: {text}")
    return "\n".join(lines)


def _format_open_tasks(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "(no open tasks in this project)"
    lines = []
    for t in tasks:
        lines.append(
            f"- id={t['id']} title=\"{t.get('title','')}\" "
            f"status={t.get('status','?')} assignee={t.get('assignee') or '—'} "
            f"source_recording={t.get('source_recording_id') or '—'}"
        )
    return "\n".join(lines)


def _format_prior_recordings(prior: list[dict[str, Any]]) -> str:
    if not prior:
        return "(no prior recordings in this project)"
    lines = []
    for p in prior:
        title = p.get("meeting_title") or p.get("filename") or "(untitled)"
        outcome_lines = []
        for o in (p.get("outcomes") or [])[:6]:
            otype = o.get("type", "?")
            otitle = o.get("title", "")
            outcome_lines.append(f"  · ({otype}) {otitle}")
        body = "\n".join(outcome_lines) or "  · (no outcomes)"
        lines.append(f"- id={p['id']} title=\"{title}\"\n{body}")
    return "\n".join(lines)


def build_context(job_id: str) -> dict[str, Any]:
    """Pull together everything the detect call needs.

    Returns a dict with the raw project objects plus a `prompt_text`
    field that's the formatted user message for the LLM.
    """
    from frontend_sync import list_project_tasks

    job = get_job(job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")
    project_id = job.get("project_id")
    result = job.get("result") or {}

    segments = result.get("segments", []) or []
    truncated = _truncate_segments(segments)
    transcript_block = _format_transcript(truncated)

    signals = {
        "is_follow_up": bool(result.get("is_follow_up")),
        "is_retro": bool(result.get("is_retro")),
        "referenced_prior_topics": result.get("referenced_prior_topics") or [],
        "unresolved_commitments": result.get("unresolved_commitments") or [],
    }

    open_tasks: list[dict[str, Any]] = []
    prior_recordings: list[dict[str, Any]] = []
    if project_id:
        open_tasks = list_project_tasks(project_id, since_days=60)
        prior_recordings = list_same_project_recordings(project_id, job_id, limit=10)

    prompt_text = "\n\n".join([
        "## Current meeting transcript",
        transcript_block or "(empty transcript)",
        "## Extraction signals (from prior LLM pass)",
        json.dumps(signals, ensure_ascii=False, indent=2),
        "## Open + recent project tasks",
        _format_open_tasks(open_tasks),
        "## Prior recordings in this project (newest first)",
        _format_prior_recordings(prior_recordings),
    ])

    return {
        "job": job,
        "project_id": project_id,
        "segments": segments,
        "signals": signals,
        "open_tasks": open_tasks,
        "prior_recordings": prior_recordings,
        "prompt_text": prompt_text,
    }


# ---------------------------------------------------------------------------
# Detect call (single submit-tool)
# ---------------------------------------------------------------------------


SUBMIT_FINDINGS_TOOL: dict[str, Any] = {
    "name": "submit_findings",
    "description": "Submit your structured analysis of the meeting. Call this exactly once.",
    "parameters": {
        "type": "object",
        "required": ["task_matches", "proposed_new_tasks", "follow_up_to_recordings"],
        "properties": {
            "task_matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["task_id", "action", "evidence_segments", "reason"],
                    "properties": {
                        "task_id": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": ["discussed", "appears_done", "appears_blocked", "none"],
                        },
                        "evidence_segments": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "reason": {"type": "string"},
                    },
                },
            },
            "proposed_new_tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "title",
                        "owner_name",
                        "source_segment_index",
                        "verb_phrase",
                        "reason",
                    ],
                    "properties": {
                        "title": {"type": "string"},
                        "owner_name": {"type": "string"},
                        "source_segment_index": {"type": "integer"},
                        "verb_phrase": {"type": "string"},
                        "reason": {"type": "string"},
                        "duplicate_of_task_id": {"type": ["string", "null"]},
                    },
                },
            },
            "follow_up_to_recordings": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
        },
    },
}


def run_detect(context: dict[str, Any], llm: Any) -> dict[str, Any]:
    """Invoke the LLM with the submit_findings tool. Returns:
        {
            "payload": {...},          # parsed tool arguments
            "tokens_in": int,
            "tokens_out": int,
            "cost_usd": float,
            "model": str,
        }

    If the LLM never calls submit_findings (rare), returns an empty
    payload with zero counts and the loop result tokens.
    """
    captured: dict[str, Any] = {"payload": None}

    def handler(name: str, args: dict[str, Any]) -> Any:
        if name == "submit_findings":
            captured["payload"] = args
            return {"ok": True}
        return {"error": f"unknown tool: {name}"}

    result: LoopResult = llm.run_tool_use_loop(
        system=DETECT_SYSTEM_PROMPT,
        user=context["prompt_text"],
        tools=[SUBMIT_FINDINGS_TOOL],
        tool_handler=handler,
        max_iterations=3,
    )

    payload = captured["payload"] or {
        "task_matches": [],
        "proposed_new_tasks": [],
        "follow_up_to_recordings": [],
    }
    cost = estimate_cost_usd(result.model, result.tokens_in, result.tokens_out)
    return {
        "payload": payload,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": cost,
        "model": result.model,
    }
