"""LLM extraction logic using Phi-4-mini via llama-cpp-python."""

import json
import uuid
from typing import Any

from storage import get_job

SYSTEM_PROMPT = """You are an AI meeting analyst. Extract structured outcomes from the transcript below.

For each outcome, identify:
- type: one of "decision", "action_item", "requirement", "blocker"
- title: concise summary (max 10 words)
- detail: 1-2 sentence explanation
- confidence: score from 0.0 to 1.0 (use below 0.80 for ambiguous or uncertain items)
- evidence_refs: list of transcript segment references supporting this outcome

Rules:
- Only extract items clearly stated or strongly implied in the transcript
- Each evidence_ref must include segment_index (0-based), speaker name, and timestamp
- A decision is a confirmed choice or agreement
- An action_item is a task assigned or volunteered by someone
- A requirement is a stated need or constraint for the project
- A blocker is an impediment or risk that could prevent progress
- Be conservative with confidence scores -- if wording is tentative, score below 0.80

Return valid JSON matching the provided schema."""

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "outcomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "decision",
                            "action_item",
                            "requirement",
                            "blocker",
                        ],
                    },
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "segment_index": {"type": "integer"},
                                "speaker": {"type": "string"},
                                "timestamp": {"type": "number"},
                                "text_snippet": {"type": "string"},
                            },
                            "required": [
                                "segment_index",
                                "speaker",
                                "timestamp",
                            ],
                        },
                    },
                },
                "required": [
                    "type",
                    "title",
                    "detail",
                    "confidence",
                    "evidence_refs",
                ],
            },
        }
    },
    "required": ["outcomes"],
}


def format_transcript_for_prompt(segments: list[dict[str, Any]]) -> str:
    """Format transcript segments as '[index] mm:ss Speaker: text' lines."""
    lines = []
    for i, seg in enumerate(segments):
        ts = seg.get("start", 0.0)
        minutes = int(ts) // 60
        seconds = int(ts) % 60
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "")
        lines.append(f"[{i}] {minutes}:{seconds:02d} {speaker}: {text}")
    return "\n".join(lines)


def format_backlink(recording_title: str, timestamp: float, speaker: str) -> str:
    """Return backlink string: 'From: {title} @ {m}:{ss} -- {speaker}'."""
    minutes = int(timestamp) // 60
    seconds = int(timestamp) % 60
    return f"From: {recording_title} @ {minutes}:{seconds:02d} -- {speaker}"


def run_extraction(job_id: str, app_state: object) -> list[dict[str, Any]]:
    """Run LLM extraction on a completed transcript.

    Gets transcript segments from storage, formats a prompt, calls the LLM
    with JSON schema constraint, validates segment indices, and returns
    a list of outcome dicts.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    result = job.get("result")
    if result is None:
        raise ValueError(f"Job {job_id} has no transcript result")

    segments = result.get("segments", [])
    if not segments:
        return []

    transcript_text = format_transcript_for_prompt(segments)
    num_segments = len(segments)

    # Build chat messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Extract outcomes from this transcript:\n\n{transcript_text}",
        },
    ]

    # Call LLM with JSON schema constraint
    response = app_state.llm.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object", "schema": EXTRACTION_SCHEMA},
        temperature=0.1,
        max_tokens=4096,
    )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)

    outcomes = []
    for item in parsed.get("outcomes", []):
        # Filter out evidence refs with invalid segment indices
        valid_refs = [
            ref
            for ref in item.get("evidence_refs", [])
            if 0 <= ref.get("segment_index", -1) < num_segments
        ]

        outcome = {
            "id": str(uuid.uuid4()),
            "type": item["type"],
            "title": item["title"],
            "detail": item["detail"],
            "confidence": item["confidence"],
            "evidence_refs": valid_refs,
            "promoted": False,
            "promoted_id": None,
        }
        outcomes.append(outcome)

    return outcomes
