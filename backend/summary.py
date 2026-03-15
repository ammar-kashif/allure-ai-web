"""LLM-powered meeting summary generation from transcript segments."""

import json
import logging
from typing import Any

from extraction import format_transcript_for_prompt
from storage import get_job

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are an AI meeting analyst. Given a meeting transcript, produce a concise summary and key topics.

Provide:
- summary: 3-5 sentences capturing the main discussion, decisions, and outcomes
- key_topics: 3-8 short phrases or topics discussed (e.g. "Project timeline", "Resource allocation")

Return valid JSON matching the provided schema exactly."""

SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_topics": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "key_topics"],
}


def run_summary(job_id: str, app_state: object) -> dict[str, Any]:
    """Generate a meeting summary from the transcript using the LLM.

    Returns a dict with keys: summary (str), key_topics (list[str]).
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    result = job.get("result")
    if result is None:
        raise ValueError(f"Job {job_id} has no transcript result")

    segments = result.get("segments", [])
    if not segments:
        return {"summary": "No transcript content available.", "key_topics": []}

    transcript_text = format_transcript_for_prompt(segments)

    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Summarize this meeting transcript:\n\n{transcript_text}"},
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object", "schema": SUMMARY_SCHEMA},
        temperature=0.2,
        max_tokens=1024,
    )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)

    return {
        "summary": parsed.get("summary", ""),
        "key_topics": parsed.get("key_topics", []) or [],
    }
