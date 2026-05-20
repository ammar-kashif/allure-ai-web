"""Tools exposed to the Ghost agent.

Each tool is a small, focused function with a JSON-schema signature the
LLM provider can call directly. Tool results carry explicit citation
fields (recording_id, segment_index, timestamp, speaker, attachment_id)
so the synthesizer answer can cite without hallucinating.

Sub-agent escalation lives in `subagent.py`; this module declares its
schema as a tool entry but the agent layer routes the actual call.
"""

from typing import Any, Optional

from entities import store as entities_store
from ghost.retrieval import (
    FTSRetriever,
    HybridRetriever,
    Scope,
    StructuredRetriever,
)
from segments_store import get_segment_window, list_segments


def _scope_from_args(args: dict[str, Any]) -> Scope:
    """Parse the agent's `scope` arg (object or null) into a Scope."""
    s = args.get("scope") or {}
    return Scope(
        recording_ids=s.get("recording_ids"),
        project_ids=s.get("project_ids"),
        since_iso=s.get("since_iso"),
        until_iso=s.get("until_iso"),
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def resolve_entity(name: str, kind: Optional[str] = None) -> dict[str, Any]:
    """Return candidate entities matching `name`. If kind is given, restrict to it.

    Always returns up to 5 candidates so the agent can disambiguate without
    extra calls.
    """
    candidates: list[dict[str, Any]] = []
    kinds_to_try = [kind] if kind else list(entities_store.VALID_KINDS)
    for k in kinds_to_try:
        hit = entities_store.find_by_exact_name(name, k)
        if hit:
            candidates.append({**hit, "match_type": "exact"})
            continue
        alias = entities_store.find_by_alias(name, k)
        if alias:
            candidates.append({**alias, "match_type": "alias"})
            continue
        fuzz = entities_store.find_by_fuzzy(name, k)
        if fuzz:
            cand, score = fuzz
            candidates.append({**cand, "match_type": "fuzzy", "match_score": score})
    # Dedupe by entity id
    seen = set()
    out = []
    for c in candidates:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
    return {"candidates": out[:5]}


def list_recent_activity(
    entity_id: str,
    source_types: Optional[list[str]] = None,
    limit: int = 10,
    since_iso: Optional[str] = None,
) -> dict[str, Any]:
    s = StructuredRetriever()
    items = s.list_recent_activity(
        entity_id, source_types=source_types, limit=limit, since_iso=since_iso
    )
    return {"items": items, "count": len(items)}


def search_transcripts(query: str, scope: Optional[dict] = None, k: int = 8) -> dict[str, Any]:
    h = HybridRetriever()
    items = h.search_transcripts(query, scope=_scope_from_args({"scope": scope}), k=k)
    return {"items": items, "count": len(items)}


def search_attachments(query: str, scope: Optional[dict] = None, k: int = 5) -> dict[str, Any]:
    h = HybridRetriever()
    items = h.search_attachments(query, scope=_scope_from_args({"scope": scope}), k=k)
    return {"items": items, "count": len(items)}


def search_outcomes(
    query: Optional[str] = None,
    scope: Optional[dict] = None,
    outcome_type: Optional[str] = None,
    k: int = 10,
) -> dict[str, Any]:
    h = HybridRetriever()
    items = h.search_outcomes(query, scope=_scope_from_args({"scope": scope}), outcome_type=outcome_type, k=k)
    return {"items": items, "count": len(items)}


def get_recording_summary(recording_id: str) -> dict[str, Any]:
    s = StructuredRetriever()
    rows = s.list_recordings(scope=Scope(recording_ids=[recording_id]), limit=1)
    if not rows:
        return {"found": False}
    return {"found": True, **rows[0]}


def get_transcript_window(recording_id: str, t_start: float, t_end: float) -> dict[str, Any]:
    segs = get_segment_window(recording_id, t_start, t_end)
    return {"items": segs, "count": len(segs)}


def list_recordings(scope: Optional[dict] = None, limit: int = 20) -> dict[str, Any]:
    s = StructuredRetriever()
    items = s.list_recordings(scope=_scope_from_args({"scope": scope}), limit=limit)
    return {"items": items, "count": len(items)}


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


# Tool name -> python callable. Sub-agent escalation is intercepted by the
# agent layer before this dispatch is reached.
TOOL_HANDLERS = {
    "resolve_entity": lambda a: resolve_entity(a.get("name", ""), a.get("kind")),
    "list_recent_activity": lambda a: list_recent_activity(
        a["entity_id"], a.get("source_types"), int(a.get("limit", 10)), a.get("since_iso")
    ),
    "search_transcripts": lambda a: search_transcripts(
        a.get("query", ""), a.get("scope"), int(a.get("k", 8))
    ),
    "search_attachments": lambda a: search_attachments(
        a.get("query", ""), a.get("scope"), int(a.get("k", 5))
    ),
    "search_outcomes": lambda a: search_outcomes(
        a.get("query"), a.get("scope"), a.get("outcome_type"), int(a.get("k", 10))
    ),
    "get_recording_summary": lambda a: get_recording_summary(a["recording_id"]),
    "get_transcript_window": lambda a: get_transcript_window(
        a["recording_id"], float(a["t_start"]), float(a["t_end"])
    ),
    "list_recordings": lambda a: list_recordings(a.get("scope"), int(a.get("limit", 20))),
}


# ---------------------------------------------------------------------------
# Tool schemas (provider-agnostic JSON Schema)
# ---------------------------------------------------------------------------


SCOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "recording_ids": {"type": "array", "items": {"type": "string"}},
        "project_ids": {"type": "array", "items": {"type": "string"}},
        "since_iso": {"type": "string", "description": "ISO 8601 lower bound"},
        "until_iso": {"type": "string", "description": "ISO 8601 upper bound"},
    },
}


CORE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "resolve_entity",
        "description": "Look up an entity (person, project, money, date, deliverable, org, document) by name. Returns up to 5 candidates with match type (exact/alias/fuzzy).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["person", "project", "money", "date", "deliverable", "org", "document"],
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_recent_activity",
        "description": "Recent mentions across all sources for a known entity_id (use resolve_entity first). Returns mentions with recording_title, timestamp, snippet.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string"},
                "source_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["segment", "outcome", "attachment_chunk", "task"]},
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "since_iso": {"type": "string"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "search_transcripts",
        "description": "Hybrid (vector + FTS) search over transcript segments. Returns segments with citations.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": SCOPE_SCHEMA,
                "k": {"type": "integer", "minimum": 1, "maximum": 25, "default": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_attachments",
        "description": "Search uploaded documents attached to recordings.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": SCOPE_SCHEMA,
                "k": {"type": "integer", "minimum": 1, "maximum": 15, "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_outcomes",
        "description": "Search extracted outcomes (decisions, action_items, requirements, blockers). Pass outcome_type to filter.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": SCOPE_SCHEMA,
                "outcome_type": {
                    "type": "string",
                    "enum": ["decision", "action_item", "requirement", "blocker"],
                },
                "k": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            },
        },
    },
    {
        "name": "get_recording_summary",
        "description": "Title, description, duration, entity count, outcome count for one recording.",
        "parameters": {
            "type": "object",
            "properties": {"recording_id": {"type": "string"}},
            "required": ["recording_id"],
        },
    },
    {
        "name": "get_transcript_window",
        "description": "Return transcript segments overlapping a time window [t_start, t_end] in seconds. Used to expand context around a search hit.",
        "parameters": {
            "type": "object",
            "properties": {
                "recording_id": {"type": "string"},
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
            },
            "required": ["recording_id", "t_start", "t_end"],
        },
    },
    {
        "name": "list_recordings",
        "description": "List recordings, optionally scoped by project or time window.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": SCOPE_SCHEMA,
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            },
        },
    },
]


SUBAGENT_TOOL: dict[str, Any] = {
    "name": "spawn_research_subagents",
    "description": (
        "Escalation for cross-project aggregation/synthesis. Spawns parallel "
        "sub-agents that each investigate one task and return distilled "
        "findings + citations. Use ONLY for questions that genuinely "
        "decompose into independent investigations. Capped at 6 sub-agents."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "scope": SCOPE_SCHEMA,
                    },
                    "required": ["question"],
                },
            }
        },
        "required": ["tasks"],
    },
}


def tools_for_intent(*, can_spawn_subagents: bool) -> list[dict[str, Any]]:
    """Return the tool list the agent gets for this turn. spawn_research_subagents
    is gated by the triage step -- the agent only sees it when escalation is
    permitted, which keeps it from over-firing on simple lookups.
    """
    if can_spawn_subagents:
        return CORE_TOOLS + [SUBAGENT_TOOL]
    return CORE_TOOLS
