"""Entity extraction LLM pass over segments + outcomes.

Runs as the `entitize` job type after `extract` completes. Uses the same
in-process LLM that extraction uses (Phi-4-mini today via llama-cpp);
swappable for a hosted call if `app_state.ghost_llm` is set.

Output schema is constrained via the LLM's JSON-schema mode. Each entity
mention is resolved against the existing entity index (exact → alias →
fuzzy → create) and written to entity_mentions.
"""

import json
import logging
import re
from typing import Any, Optional

from observability import step_timer
from storage import get_job

from . import store

logger = logging.getLogger(__name__)


ENTITY_SYSTEM_PROMPT = """You extract entities from meeting transcripts.

From the segments and outcomes provided, identify mentions of:
- person: named individuals (first name, last name, full name, or distinctive title)
- project: named projects, codenames, or workstreams
- money: monetary amounts ("$400", "twelve thousand dollars")
- date: specific dates or date references ("April 14", "next Thursday")
- deliverable: specific artifacts being produced ("the PRD", "Q3 report")
- org: organizations, companies, teams ("Acme", "the legal team")
- document: referenced documents ("the auth spec", "the design doc")

For each mention return:
- name (string): the surface form as it appears in the transcript
- kind (enum): one of person | project | money | date | deliverable | org | document
- canonical_name (string): preferred name to use as the entity's identity
- aliases (string[]): other forms of the same entity if visible
- segment_index (int|null): which segment contained the mention (0-based)
- snippet (string): ~120 chars of surrounding context

Be conservative. Only extract clearly named entities; skip generic
references ("the customer", "someone"). An empty list is the right answer
for transcripts with no named entities."""


ENTITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mentions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": list(store.VALID_KINDS),
                    },
                    "canonical_name": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "segment_index": {"type": ["integer", "null"]},
                    "snippet": {"type": "string"},
                },
                "required": ["name", "kind", "canonical_name", "segment_index"],
            },
        }
    },
    "required": ["mentions"],
}


# Cheap regex-based extraction for very-high-confidence patterns. Run first
# so we don't burn LLM tokens on things we can find deterministically.
MONEY_RE = re.compile(r"\$\s?[\d,]+(?:\.\d{1,2})?(?:\s?(?:k|K|m|M|million|thousand))?")


def deterministic_pre_pass(
    segments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Pull obvious literal entities from segments before any LLM call.

    Currently handles monetary amounts via regex. Returns mention dicts in
    the same shape as the LLM output so they merge cleanly.
    """
    mentions: list[dict[str, Any]] = []
    for idx, seg in enumerate(segments):
        text = seg.get("text") or ""
        for m in MONEY_RE.finditer(text):
            amount = m.group(0).strip()
            snippet_start = max(0, m.start() - 60)
            snippet_end = min(len(text), m.end() + 60)
            mentions.append(
                {
                    "name": amount,
                    "kind": "money",
                    "canonical_name": amount,
                    "aliases": [],
                    "segment_index": idx,
                    "snippet": text[snippet_start:snippet_end],
                }
            )
    return mentions


def _format_for_llm(
    segments: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> str:
    lines = ["## Segments"]
    for i, seg in enumerate(segments[:200]):  # cap for context budget
        speaker = seg.get("speaker", "?")
        text = (seg.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"[{i}] {speaker}: {text}")
    if outcomes:
        lines.append("\n## Outcomes")
        for o in outcomes:
            t = o.get("type", "?")
            title = o.get("title", "")
            detail = o.get("detail", "")
            lines.append(f"- ({t}) {title}: {detail}")
    return "\n".join(lines)


def call_llm_for_entities(
    llm: Any, segments: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Round-trip the LLM. Returns mention dicts. Empty list on failure
    (never raises -- caller can still write deterministic mentions)."""
    if llm is None:
        return []
    user_content = _format_for_llm(segments, outcomes)
    messages = [
        {"role": "system", "content": ENTITY_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    try:
        response = llm.create_chat_completion(
            messages=messages,
            response_format={"type": "json_object", "schema": ENTITY_SCHEMA},
            temperature=0.0,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("entity LLM call failed")
        return []
    try:
        raw = response["choices"][0]["message"]["content"]
        parsed = json.loads(raw)
        return parsed.get("mentions", []) or []
    except Exception:
        logger.exception("entity LLM response unparseable")
        return []


def run_entitize(
    recording_id: str,
    app_state: object,
    *,
    project_id: Optional[str] = None,
) -> dict[str, Any]:
    """Top-level entitize pass for a single recording.

    Reads transcript segments + outcomes from the job row, optionally calls
    the LLM, merges with deterministic mentions, resolves each candidate
    against the entity index, and writes entity_mentions rows.

    Idempotent: deletes all existing mentions for the recording first so
    re-running on a corrected transcript doesn't double-count.

    Returns a stats dict: { mentions_written, entities_created, entities_reused }.
    """
    job = get_job(recording_id)
    if job is None:
        raise ValueError(f"Recording {recording_id} not found")
    result = job.get("result") or {}
    segments: list[dict[str, Any]] = result.get("segments", []) or []
    outcomes: list[dict[str, Any]] = job.get("outcomes", []) or []

    # Recover project_id from the job row when caller didn't supply one.
    if project_id is None:
        project_id = job.get("project_id")

    # Idempotency: wipe prior mentions for this recording. New entities
    # are NOT deleted -- they remain as canonical records, possibly
    # referenced by other recordings.
    store.delete_mentions_for_recording(recording_id)

    # Deterministic mentions first (free, never wrong about literal $ amounts).
    deterministic = deterministic_pre_pass(segments)

    # Then LLM pass. Prefer ghost_llm (hosted) when set; fall back to local.
    llm = getattr(app_state, "ghost_llm", None) or getattr(app_state, "llm", None)
    with step_timer("entitize.llm", recording_id=recording_id, n_segments=len(segments)):
        llm_mentions = call_llm_for_entities(llm, segments, outcomes)

    candidates = deterministic + llm_mentions
    mentions_written = 0
    entities_created = 0
    entities_reused = 0

    for c in candidates:
        try:
            name = (c.get("name") or "").strip()
            kind = c.get("kind", "")
            canonical = (c.get("canonical_name") or name).strip()
            if not name or kind not in store.VALID_KINDS:
                continue
            seg_idx = c.get("segment_index")
            snippet = c.get("snippet", "")

            existing_count = len(store.list_entities(kind=kind, limit=10000))
            entity = store.resolve_or_create(canonical, kind, aliases=c.get("aliases", []))
            if len(store.list_entities(kind=kind, limit=10000)) > existing_count:
                entities_created += 1
            else:
                entities_reused += 1

            timestamp = None
            speaker = None
            if isinstance(seg_idx, int) and 0 <= seg_idx < len(segments):
                seg = segments[seg_idx]
                timestamp = float(seg.get("start", 0.0))
                speaker = seg.get("speaker")

            store.add_mention(
                entity_id=entity["id"],
                source_type="segment" if seg_idx is not None else "outcome",
                source_id=f"{recording_id}:{seg_idx}" if seg_idx is not None else recording_id,
                recording_id=recording_id,
                project_id=project_id,
                timestamp=timestamp,
                speaker=speaker,
                confidence=float(c.get("confidence", 1.0)),
                snippet=snippet,
            )
            mentions_written += 1
        except Exception:
            logger.exception("entitize: failed mention candidate %r", c)

    # Also index outcomes into FTS so Ghost's search_outcomes can return
    # them with rank-aware scoring.
    if outcomes:
        store.index_outcomes(recording_id, outcomes)

    # Embed segments + outcomes for vector retrieval. Opt-in via env var
    # (sentence-transformers download is heavy; tests + cold boots skip
    # unless GHOST_EMBED_ON_ENTITIZE=1). Production sets this in the
    # backend's environment.
    segments_embedded = 0
    outcomes_embedded = 0
    import os as _os
    if _os.environ.get("GHOST_EMBED_ON_ENTITIZE", "0") in ("1", "true", "yes", "on"):
        try:
            from ghost import embeddings as ghost_embeddings

            with step_timer("entitize.embed", recording_id=recording_id):
                segments_embedded = ghost_embeddings.embed_and_index_recording(recording_id)
                outcomes_embedded = ghost_embeddings.embed_outcomes(recording_id, outcomes)
        except Exception:
            logger.exception("ghost embedding pass failed for %s", recording_id)

    return {
        "mentions_written": mentions_written,
        "entities_created": entities_created,
        "entities_reused": entities_reused,
        "segments_embedded": segments_embedded,
        "outcomes_embedded": outcomes_embedded,
    }


def backfill_all_recordings(app_state: object) -> dict[str, int]:
    """Walk every completed job and run entitize. Idempotent."""
    from storage import list_jobs

    totals = {"recordings_processed": 0, "mentions_written": 0, "entities_created": 0}
    for job in list_jobs():
        if job.get("status") != "completed":
            continue
        if job.get("extraction_status") != "completed":
            continue
        try:
            stats = run_entitize(job["id"], app_state)
            totals["recordings_processed"] += 1
            totals["mentions_written"] += stats["mentions_written"]
            totals["entities_created"] += stats["entities_created"]
        except Exception:
            logger.exception("backfill_all_recordings: %s failed", job["id"])
    return totals
