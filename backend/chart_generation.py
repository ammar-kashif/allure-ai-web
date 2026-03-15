"""PlantUML decision chart generation using the shared LLM instance.

Hybrid approach:
  1. LLM produces structured JSON (decision nodes with topic, question,
     outcome, rationale, speaker, timestamp).
  2. Python builds syntactically guaranteed-valid PlantUML from that JSON.

This avoids the model writing PlantUML syntax directly, which small LLMs
do unreliably (wrong note syntax, missing delimiters, etc.).
"""

import json
import logging
import re
from typing import Any

from storage import get_job

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt & schema
# ---------------------------------------------------------------------------

CHART_SYSTEM_PROMPT = """You are a meeting analyst. Given a list of decisions made in a meeting, produce a structured JSON that describes the decision flow in chronological order.

For EACH decision output an object with these fields:
- "topic": a short phrase (3-6 words) describing what was being discussed (e.g. "Frontend framework selection")
- "question": the decision question that was posed (e.g. "Which framework to use")
- "outcome": the answer / choice that was made (e.g. "React with Next.js") -- keep it under 5 words
- "rationale": one concise sentence explaining WHY this outcome was chosen, drawn from the transcript evidence provided
- "speaker": the name of the speaker who drove or announced the decision
- "timestamp": the timestamp string (e.g. "3:45") when the decision was made

Rules:
- Include ALL decisions provided, in the order they appear chronologically
- "rationale" MUST be a real reason taken from the transcript snippets, not a generic filler phrase
- Keep all strings short -- they will appear inside a flowchart box
- Do NOT invent information not present in the input
- Return JSON only, matching the provided schema exactly"""

CHART_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "question": {"type": "string"},
                    "outcome": {"type": "string"},
                    "rationale": {"type": "string"},
                    "speaker": {"type": "string"},
                    "timestamp": {"type": "string"},
                },
                "required": [
                    "topic",
                    "question",
                    "outcome",
                    "rationale",
                    "speaker",
                    "timestamp",
                ],
            },
        },
    },
    "required": ["title", "decisions"],
}


# ---------------------------------------------------------------------------
# PlantUML builder (programmatic — no LLM syntax errors possible)
# ---------------------------------------------------------------------------

def _sanitize(text: str) -> str:
    """Remove characters that break PlantUML labels."""
    # Strip or replace characters that confuse the parser
    text = text.replace('"', "'").replace("\n", " ").replace("\r", "")
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text).strip()
    # Truncate very long strings to keep diagram readable
    if len(text) > 80:
        text = text[:77] + "..."
    return text


def _build_plantuml(title: str, decisions: list[dict[str, Any]]) -> str:
    """Construct a valid PlantUML activity diagram from structured decision data.

    Uses the new (v2) PlantUML activity diagram syntax throughout.
    """
    lines: list[str] = [
        "@startuml",
        "skinparam defaultFontName Arial",
        "skinparam ArrowColor #555555",
        "skinparam ActivityBackgroundColor #F8F9FA",
        "skinparam NoteBackgroundColor #FFFDE7",
        "skinparam NoteBorderColor #F0CC00",
        "",
        f"title {_sanitize(title)}",
        "",
        "start",
        "",
    ]

    for d in decisions:
        topic = _sanitize(d.get("topic", "Discussion"))
        question = _sanitize(d.get("question", "Decision?"))
        outcome = _sanitize(d.get("outcome", "Agreed"))
        rationale = _sanitize(d.get("rationale", ""))
        speaker = _sanitize(d.get("speaker", "Unknown"))
        timestamp = _sanitize(d.get("timestamp", ""))

        # Activity node: what was being discussed
        lines.append(f":{topic};")

        # Decision diamond with outcome
        lines.append(f"if ({question}?) then ({outcome})")

        # Outcome action
        lines.append(f"  :{outcome};")

        # Note with speaker, timestamp, and rationale
        lines.append("  note right")
        lines.append(f"    **{speaker}** @ {timestamp}")
        if rationale:
            lines.append(f"    //\"{rationale}\"//")
        lines.append("  end note")

        lines.append("end if")
        lines.append("")

    lines += ["stop", "@enduml"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Context formatter (includes transcript snippets)
# ---------------------------------------------------------------------------

def _format_decisions_for_prompt(
    decisions: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> str:
    """Format decisions into a prompt-friendly numbered list.

    Includes the decision title, detail, all evidence refs with their
    text_snippets, and the speaker + timestamp.
    """
    lines: list[str] = []
    for i, d in enumerate(decisions, start=1):
        title = d.get("title", "Untitled decision")
        detail = d.get("detail", "")
        refs = d.get("evidence_refs", [])

        # Format the primary ref
        primary_speaker = "Unknown"
        primary_ts = "0:00"
        if refs:
            ref = refs[0]
            primary_speaker = ref.get("speaker", "Unknown")
            ts = ref.get("timestamp", 0.0)
            primary_ts = f"{int(ts) // 60}:{int(ts) % 60:02d}"

        entry = [
            f"{i}. Decision: {title}",
            f"   Detail: {detail}",
            f"   Primary speaker: {primary_speaker} @ {primary_ts}",
        ]

        # Append all evidence snippets so the LLM can extract real rationale
        if refs:
            entry.append("   Transcript evidence:")
            for ref in refs[:3]:  # Cap at 3 snippets per decision
                snippet = ref.get("text_snippet", "").strip()
                ref_speaker = ref.get("speaker", "Unknown")
                ref_ts_raw = ref.get("timestamp", 0.0)
                ref_ts = f"{int(ref_ts_raw) // 60}:{int(ref_ts_raw) % 60:02d}"
                if snippet:
                    entry.append(f"     - [{ref_ts}] {ref_speaker}: \"{snippet}\"")

        lines.append("\n".join(entry))

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_chart_generation(job_id: str, app_state: object) -> str:
    """Generate a PlantUML decision chart from extracted outcomes.

    1. Load decisions from storage.
    2. Ask LLM to produce a structured JSON flow.
    3. Programmatically build valid PlantUML from that JSON.
    4. Return the PlantUML string (stored in DB by caller).
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    outcomes = job.get("outcomes", [])
    decisions = [o for o in outcomes if o.get("type") == "decision"]

    result = job.get("result") or {}
    segments = result.get("segments", [])
    filename = job.get("original_filename", "Meeting")

    # --- No decisions: return a minimal placeholder diagram ---
    if not decisions:
        logger.info("Job %s has no decisions; generating placeholder chart", job_id)
        return _build_plantuml(
            title=filename,
            decisions=[
                {
                    "topic": "Meeting discussion",
                    "question": "Were formal decisions recorded",
                    "outcome": "No formal decisions",
                    "rationale": "All topics were discussed without reaching a recorded decision",
                    "speaker": "—",
                    "timestamp": "—",
                }
            ],
        )

    # Limit to 15 decisions to keep the diagram readable and the prompt short
    decisions = decisions[:15]

    decisions_text = _format_decisions_for_prompt(decisions, segments)

    messages = [
        {"role": "system", "content": CHART_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Meeting recording: {filename}\n\n"
                f"Decisions to include in the chart:\n\n{decisions_text}\n\n"
                "Produce the structured JSON decision flow."
            ),
        },
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object", "schema": CHART_SCHEMA},
        temperature=0.1,
        max_tokens=2048,
    )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)

    chart_title = parsed.get("title") or filename
    chart_decisions = parsed.get("decisions", [])

    if not chart_decisions:
        raise ValueError("LLM returned an empty decisions list")

    plantuml = _build_plantuml(chart_title, chart_decisions)

    logger.info(
        "Chart generation complete for job %s (%d decisions, %d chars)",
        job_id,
        len(chart_decisions),
        len(plantuml),
    )
    return plantuml
