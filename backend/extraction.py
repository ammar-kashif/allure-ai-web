"""LLM extraction logic using Phi-4-mini via llama-cpp-python."""

import json
import logging
import os
import uuid
from typing import Any

from observability import step_timer
from storage import get_job

logger = logging.getLogger(__name__)

WORD_CORRECTIONS_ENABLED = (
    os.environ.get("EXTRACTION_WORD_CORRECTIONS", "1").lower() in ("1", "true", "yes", "on")
)
WORD_CORRECTION_MIN_CONFIDENCE = float(
    os.environ.get("EXTRACTION_WORD_CORRECTION_MIN_CONFIDENCE", "0.85")
)

SYSTEM_PROMPT_BASE = """You are an AI meeting analyst. From the transcript below, produce a structured JSON object with these fields:

1. meeting_title (string): a 5-to-8-word title that summarizes the meeting's main subject. Use title case. No quotes.
2. meeting_description (string): a 1-2 sentence factual description of what was discussed. No filler ("In this meeting, ..."); be direct.
3. outcomes (array): a list of decisions, action items, requirements, and blockers from the meeting.

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
"""

SYSTEM_PROMPT_CORRECTIONS = """
4. transcript_corrections (array, may be empty): up to 10 OBVIOUS speech-to-text errors you can fix. ONLY include:
- A wrong word that doesn't fit the surrounding context (homophone confusions like "their" vs "there", mis-recognized proper nouns).
- A clearly dropped or duplicated word that breaks a sentence.
DO NOT include stylistic rewrites, paraphrases, punctuation-only changes, or capitalization-only changes (those are handled separately). DO NOT correct slang, filler words, or grammar quirks of natural speech.
Each correction must include: segment_index (0-based), original_text (verbatim from that segment), corrected_text, confidence (>= 0.85 only — omit if unsure), reason (≤ 12 words).
Be very conservative. An empty array is the right answer for clean transcripts.
"""

SYSTEM_PROMPT_FOOTER = "\nReturn valid JSON matching the provided schema."

SYSTEM_PROMPT = (
    SYSTEM_PROMPT_BASE
    + (SYSTEM_PROMPT_CORRECTIONS if WORD_CORRECTIONS_ENABLED else "")
    + SYSTEM_PROMPT_FOOTER
)

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "meeting_title": {"type": "string"},
        "meeting_description": {"type": "string"},
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
        },
    },
    "required": ["meeting_title", "meeting_description", "outcomes"],
}

if WORD_CORRECTIONS_ENABLED:
    EXTRACTION_SCHEMA["properties"]["transcript_corrections"] = {
        "type": "array",
        "maxItems": 10,
        "items": {
            "type": "object",
            "properties": {
                "segment_index": {"type": "integer"},
                "original_text": {"type": "string"},
                "corrected_text": {"type": "string"},
                "confidence": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": [
                "segment_index",
                "original_text",
                "corrected_text",
                "confidence",
                "reason",
            ],
        },
    }
    EXTRACTION_SCHEMA["required"].append("transcript_corrections")


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


def run_extraction(job_id: str, app_state: object) -> dict[str, Any]:
    """Run LLM extraction on a completed transcript.

    Returns a dict with:
        outcomes: list of outcome dicts (existing shape)
        meeting_title: auto-generated 5-8 word title
        meeting_description: auto-generated 1-2 sentence summary
        corrections_applied: list of word corrections that were applied
            in-place to the stored transcript segments (filtered by confidence).
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    result = job.get("result")
    if result is None:
        raise ValueError(f"Job {job_id} has no transcript result")

    segments = result.get("segments", [])
    if not segments:
        return {
            "outcomes": [],
            "meeting_title": "",
            "meeting_description": "",
            "corrections_applied": [],
        }

    transcript_text = format_transcript_for_prompt(segments)
    num_segments = len(segments)

    # Build chat messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Analyze this transcript:\n\n{transcript_text}",
        },
    ]

    # Call LLM with JSON schema constraint
    with step_timer(
        "extraction.llm",
        job_id=job_id,
        n_segments=num_segments,
        corrections_enabled=int(WORD_CORRECTIONS_ENABLED),
    ):
        response = app_state.llm.create_chat_completion(
            messages=messages,
            response_format={"type": "json_object", "schema": EXTRACTION_SCHEMA},
            temperature=0.1,
            max_tokens=4096,
        )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)

    outcomes: list[dict[str, Any]] = []
    for item in parsed.get("outcomes", []):
        valid_refs = [
            ref
            for ref in item.get("evidence_refs", [])
            if 0 <= ref.get("segment_index", -1) < num_segments
        ]
        outcomes.append(
            {
                "id": str(uuid.uuid4()),
                "type": item["type"],
                "title": item["title"],
                "detail": item["detail"],
                "confidence": item["confidence"],
                "evidence_refs": valid_refs,
                "promoted": False,
                "promoted_id": None,
            }
        )

    # Apply high-confidence word corrections in place (mutates `segments`)
    corrections_applied: list[dict[str, Any]] = []
    if WORD_CORRECTIONS_ENABLED:
        for c in parsed.get("transcript_corrections", []) or []:
            idx = c.get("segment_index", -1)
            conf = float(c.get("confidence", 0.0))
            corrected = (c.get("corrected_text") or "").strip()
            original_claim = (c.get("original_text") or "").strip()
            if not (0 <= idx < num_segments):
                continue
            if conf < WORD_CORRECTION_MIN_CONFIDENCE:
                continue
            if not corrected:
                continue
            actual_text = segments[idx].get("text", "")
            # Only apply if the model's claim of original matches what we have
            # (case-insensitive, ignoring trailing punctuation) — avoids
            # rewriting unrelated content.
            if original_claim and not _texts_match_loosely(original_claim, actual_text):
                logger.info(
                    "Skip correction idx=%d: original_text mismatch (model=%r, actual=%r)",
                    idx, original_claim, actual_text,
                )
                continue
            segments[idx]["text"] = corrected
            corrections_applied.append(
                {
                    "segment_index": idx,
                    "from": actual_text,
                    "to": corrected,
                    "confidence": conf,
                    "reason": c.get("reason", ""),
                }
            )
        if corrections_applied:
            logger.info(
                "Applied %d transcript correction(s) for job %s",
                len(corrections_applied),
                job_id,
            )

    # Fallback if the LLM returned an empty title/description (happens for
    # short / low-content recordings where Phi-4-mini can't pick a 5-8 word
    # title). Without a fallback, the frontend sync sees an empty string and
    # keeps the placeholder "Recording <date>" title forever.
    meeting_title = (parsed.get("meeting_title") or "").strip()
    meeting_description = (parsed.get("meeting_description") or "").strip()

    if not meeting_title:
        meeting_title = _fallback_title_from_segments(segments)
        logger.info(
            "LLM produced empty meeting_title for %s; using fallback %r",
            job_id,
            meeting_title,
        )
    if not meeting_description:
        meeting_description = _fallback_description_from_segments(segments)

    return {
        "outcomes": outcomes,
        "meeting_title": meeting_title,
        "meeting_description": meeting_description,
        "corrections_applied": corrections_applied,
    }


def _fallback_title_from_segments(segments: list[dict[str, Any]]) -> str:
    """Deterministic 5-8 word title from the longest early speech segment.
    Never returns empty — the worst case is the literal first words spoken."""
    if not segments:
        return "Conversation"
    early = segments[: max(3, len(segments) // 2)] or segments[:3]
    candidate = max(early, key=lambda s: len((s.get("text") or "").strip()))
    words = (candidate.get("text") or "").split()[:8]
    title = " ".join(words).rstrip(",.;:!?")
    # Punctuation step already produced sentence-cased text; only capitalize
    # the leading word to be safe.
    if title:
        title = title[0].upper() + title[1:]
        return title
    return "Conversation"


def _fallback_description_from_segments(segments: list[dict[str, Any]]) -> str:
    """Concatenate the first 2 substantive segments into a 1-sentence summary."""
    texts = [
        (s.get("text") or "").strip()
        for s in segments[:5]
        if (s.get("text") or "").strip()
    ]
    if not texts:
        return ""
    blob = " ".join(texts[:2])
    return (blob[:200].rstrip() + "...") if len(blob) > 200 else blob


def _texts_match_loosely(claim: str, actual: str) -> bool:
    """Return True if `claim` appears in `actual` (case-insensitive, ignoring
    trailing punctuation). Conservative gate before applying a correction."""
    import re as _re

    norm = lambda s: _re.sub(r"[.,!?;:]+$", "", s.strip().lower())
    c, a = norm(claim), norm(actual)
    return bool(c) and (c == a or c in a)
