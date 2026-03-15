"""Slide-to-transcript alignment using the shared LLM instance.

For each slide, the LLM identifies which transcript segments are most relevant,
producing a ranked list with relevance scores.
"""

import json
import logging
from typing import Any

from storage import get_job

logger = logging.getLogger(__name__)

ALIGNMENT_SYSTEM_PROMPT = """You are a meeting analyst. You will be given slide content from a presentation and a set of transcript segments from the same meeting.

For each slide, identify which transcript segments are most relevant to that slide's topic.

For each alignment, output:
- "slide_index": the 0-based slide index
- "segment_indices": list of 0-based transcript segment indices, ordered by relevance (most relevant first, max 5)
- "relevance_scores": parallel list of relevance scores from 0.0 to 1.0 for each matched segment
- "summary": one sentence describing how the slide content relates to the transcript

Rules:
- Only include segments with relevance >= 0.3
- Do not hallucinate; only use information present in the inputs
- Return JSON only, matching the provided schema exactly"""

ALIGNMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "alignments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slide_index": {"type": "integer"},
                    "segment_indices": {"type": "array", "items": {"type": "integer"}},
                    "relevance_scores": {"type": "array", "items": {"type": "number"}},
                    "summary": {"type": "string"},
                },
                "required": ["slide_index", "segment_indices", "relevance_scores", "summary"],
            },
        }
    },
    "required": ["alignments"],
}


def _format_slides_for_prompt(slides: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for slide in slides:
        lines.append(f"[Slide {slide['index']}] {slide['title']}")
        if slide.get("content"):
            lines.append(f"  Content: {slide['content'][:300]}")
        if slide.get("notes"):
            lines.append(f"  Notes: {slide['notes'][:200]}")
    return "\n".join(lines)


def _format_segments_for_prompt(segments: list[dict[str, Any]], max_segments: int = 60) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments[:max_segments]):
        ts = seg.get("start", 0.0)
        mins = int(ts) // 60
        secs = int(ts) % 60
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "")[:200]
        lines.append(f"[{i}] {mins}:{secs:02d} {speaker}: {text}")
    return "\n".join(lines)


def run_alignment(job_id: str, doc_index: int, app_state: object) -> list[dict[str, Any]]:
    """Align slides from a stored document against the transcript segments.

    Returns a list of alignment objects per slide.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    result = job.get("result")
    if not result:
        raise ValueError(f"Job {job_id} has no transcript")

    documents = job.get("documents")
    if not documents:
        raise ValueError(f"Job {job_id} has no documents")

    if doc_index >= len(documents):
        raise ValueError(f"Document index {doc_index} out of range")

    doc = documents[doc_index]
    slides = doc.get("slides", [])
    segments = result.get("segments", [])

    if not slides:
        return []

    # Limit slides to keep prompt manageable
    slides_text = _format_slides_for_prompt(slides[:20])
    segments_text = _format_segments_for_prompt(segments)

    messages = [
        {"role": "system", "content": ALIGNMENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Slides from document: {doc.get('filename', 'document')}\n\n"
                f"{slides_text}\n\n"
                f"Transcript segments:\n\n{segments_text}\n\n"
                "Produce the alignment JSON."
            ),
        },
    ]

    response = app_state.llm.create_chat_completion(  # type: ignore[attr-defined]
        messages=messages,
        response_format={"type": "json_object", "schema": ALIGNMENT_SCHEMA},
        temperature=0.1,
        max_tokens=2048,
    )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)
    alignments = parsed.get("alignments", [])

    logger.info(
        "Alignment complete for job %s doc %d: %d slides aligned",
        job_id,
        doc_index,
        len(alignments),
    )
    return alignments
