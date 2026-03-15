"""AI-assisted project plan generation from meeting outcomes and transcript.

The LLM proposes a structured plan with tasks, milestones, and risks.
The plan is returned to the frontend for preview/accept workflow.
"""

import json
import logging
from typing import Any

from storage import get_job

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """You are a senior project manager AI. You will receive meeting outcomes (decisions, action items, requirements, blockers) and relevant transcript excerpts from a project kick-off or planning meeting.

Generate a structured project plan with:
- **Tasks**: concrete, actionable work items derived from the meeting
- **Milestones**: logical phases or checkpoints that group related tasks
- **Risks**: potential issues or blockers identified from the meeting

For each task:
- title: short, action-oriented (max 60 chars)
- detail: brief description of what needs to be done (1-3 sentences)
- priority: "high", "medium", or "low"
- milestone: which milestone this task belongs to (use milestone title, or null)
- dueOffset: estimated days from project start (integer, or null if unknown)

For each milestone:
- title: name of the phase/checkpoint
- startOffset: days from project start (integer)
- endOffset: days from project start (integer, must be > startOffset)

For each risk:
- title: short risk description (max 60 chars)
- detail: explain the risk and potential mitigation (1-3 sentences)

Rules:
- Only derive tasks from explicit discussion points in the meeting
- Aim for 5-15 tasks, 2-5 milestones, 1-5 risks
- Be specific — avoid vague tasks like "Do research" or "Follow up"
- Return JSON only, matching the provided schema exactly"""

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "milestone": {"type": ["string", "null"]},
                    "dueOffset": {"type": ["integer", "null"]},
                },
                "required": ["title", "detail", "priority"],
            },
        },
        "milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "startOffset": {"type": "integer"},
                    "endOffset": {"type": "integer"},
                },
                "required": ["title", "startOffset", "endOffset"],
            },
        },
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["title", "detail"],
            },
        },
    },
    "required": ["tasks", "milestones", "risks"],
}


def _format_outcomes(outcomes: list[dict[str, Any]]) -> str:
    if not outcomes:
        return "(No outcomes extracted)"
    sections: dict[str, list[str]] = {}
    for o in outcomes:
        t = o.get("type", "other")
        sections.setdefault(t, []).append(o.get("text", "").strip())
    lines: list[str] = []
    label_map = {
        "decision": "Decisions",
        "action_item": "Action Items",
        "requirement": "Requirements",
        "blocker": "Blockers",
    }
    for key, label in label_map.items():
        if key in sections:
            lines.append(f"**{label}:**")
            for item in sections[key]:
                lines.append(f"  - {item}")
    return "\n".join(lines)


def _format_transcript_sample(segments: list[dict[str, Any]], max_chars: int = 3000) -> str:
    lines: list[str] = []
    total = 0
    for seg in segments:
        ts = seg.get("start", 0.0)
        mins = int(ts) // 60
        secs = int(ts) % 60
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        line = f"{mins}:{secs:02d} {speaker}: {text}"
        total += len(line)
        if total > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


def run_plan_generation(job_id: str, project_goal: str | None, app_state: object) -> dict[str, Any]:
    """Generate a project plan from the meeting's outcomes and transcript.

    Returns the structured plan JSON directly (not stored).
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    if job["status"] != "completed":
        raise ValueError(f"Job {job_id} transcript not ready (status={job['status']})")

    result = job.get("result") or {}
    outcomes = job.get("outcomes") or []
    segments = result.get("segments", [])

    outcomes_text = _format_outcomes(outcomes)
    transcript_text = _format_transcript_sample(segments)

    goal_block = f"\nProject goal: {project_goal}\n" if project_goal else ""

    messages = [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"{goal_block}\n"
                f"Meeting outcomes:\n\n{outcomes_text}\n\n"
                f"Transcript excerpt:\n\n{transcript_text}\n\n"
                "Generate the project plan JSON."
            ),
        },
    ]

    response = app_state.llm.create_chat_completion(  # type: ignore[attr-defined]
        messages=messages,
        response_format={"type": "json_object", "schema": PLAN_SCHEMA},
        temperature=0.2,
        max_tokens=2048,
    )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)

    logger.info(
        "Plan generated for job %s: %d tasks, %d milestones, %d risks",
        job_id,
        len(parsed.get("tasks", [])),
        len(parsed.get("milestones", [])),
        len(parsed.get("risks", [])),
    )
    return parsed
