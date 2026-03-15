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

If presentation slides are provided, also identify which slides relate to each outcome.
Include slide_refs listing the doc_filename, slide_index (0-based), slide_title, and a
one-sentence relevance explanation. Only add a slide_ref when there is a clear thematic
connection between the slide content and the outcome — do not force matches.

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
                    "slide_refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "doc_filename": {"type": "string"},
                                "slide_index": {"type": "integer"},
                                "slide_title": {"type": "string"},
                                "relevance": {"type": "string"},
                            },
                            "required": ["doc_filename", "slide_index"],
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


def format_documents_for_prompt(documents: list[dict[str, Any]], max_chars: int = 2000) -> str:
    """Format parsed documents as labelled slide blocks for the LLM prompt.

    Caps total output to max_chars to stay within token budget.
    """
    if not documents:
        return ""

    lines: list[str] = []
    total = 0

    for doc in documents:
        filename = doc.get("filename", "document")
        slides = doc.get("slides", [])
        header = f"\n[Doc: {filename}]"
        lines.append(header)
        total += len(header)

        for slide in slides:
            idx = slide.get("index", 0)
            title = slide.get("title", f"Slide {idx + 1}")
            content = slide.get("content", "").strip()
            notes = slide.get("notes", "").strip()

            slide_header = f"[Slide {idx}] {title}"
            lines.append(slide_header)
            total += len(slide_header)

            if content:
                content_line = f"  Content: {content[:200]}"
                lines.append(content_line)
                total += len(content_line)

            if notes:
                notes_line = f"  Notes: {notes[:150]}"
                lines.append(notes_line)
                total += len(notes_line)

            if total >= max_chars:
                lines.append("  [... remaining slides truncated ...]")
                return "\n".join(lines)

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

    # Load any uploaded documents to enrich the prompt
    documents = job.get("documents") or []
    doc_text = format_documents_for_prompt(documents)

    # Build user message — append slide content when documents are present
    if doc_text:
        user_content = (
            f"Extract outcomes from this transcript:\n\n{transcript_text}"
            f"\n\n---\nPresentation slides for context:\n{doc_text}"
        )
    else:
        user_content = f"Extract outcomes from this transcript:\n\n{transcript_text}"

    # Build chat messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
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

    # Build a lookup of valid slide counts per document filename for validation
    doc_slide_counts: dict[str, int] = {}
    for doc in documents:
        filename = doc.get("filename", "")
        if filename:
            doc_slide_counts[filename] = len(doc.get("slides", []))

    outcomes = []
    for item in parsed.get("outcomes", []):
        # Filter out evidence refs with invalid segment indices
        valid_refs = [
            ref
            for ref in item.get("evidence_refs", [])
            if 0 <= ref.get("segment_index", -1) < num_segments
        ]

        # Filter out slide refs with invalid doc filenames or slide indices
        raw_slide_refs = item.get("slide_refs", []) or []
        valid_slide_refs = []
        for ref in raw_slide_refs:
            filename = ref.get("doc_filename", "")
            slide_idx = ref.get("slide_index", -1)
            max_slides = doc_slide_counts.get(filename, 0)
            if filename and 0 <= slide_idx < max_slides:
                valid_slide_refs.append(ref)

        outcome = {
            "id": str(uuid.uuid4()),
            "type": item["type"],
            "title": item["title"],
            "detail": item["detail"],
            "confidence": item["confidence"],
            "evidence_refs": valid_refs,
            "slide_refs": valid_slide_refs,
            "promoted": False,
            "promoted_id": None,
        }
        outcomes.append(outcome)

    return outcomes
