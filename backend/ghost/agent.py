"""Ghost agent: single-agent tool-use loop with sub-agent escalation.

API:
    ask(question, conv_id=None, scope=None) -> dict
        triage -> select tools -> run loop -> persist messages -> return.

Sub-agent escalation: when the agent calls spawn_research_subagents, we
intercept the call and dispatch parallel investigations (capped at 6),
each with its own context. Sub-agents see only the core tools (no
further escalation -- depth-1).
"""

import logging
import time
from typing import Any, Optional

from ghost import conversations as ghost_convos
from ghost import llm as ghost_llm
from ghost import settings as ghost_settings
from ghost.tools import CORE_TOOLS, TOOL_HANDLERS, tools_for_intent
from ghost.triage import triage as triage_question

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Ghost, a project memory assistant for an engineering / product team.

Answer questions about meetings, decisions, action items, blockers, people,
projects, and documents from the user's recordings.

Hard rules for output:
- No preamble (no "Sure, let me look that up...", no restating the question).
- Direct answer first. Be concrete.
- Cite every claim. Inline citations like [rec: title, mm:ss, speaker] for
  transcript references, [doc: filename] for attachments, [outcome: type, title]
  for outcomes. Multiple citations per claim if available.
- Hard cap: 150 words for lookups, 400 for synthesis. Shorter is better.
- If you don't know, say so in one sentence. List what you searched.

Use tools rather than guessing. Prefer multiple parallel tool calls to
serial ones. resolve_entity first when the user names a person / project /
amount.

Tool routing rules:
- Questions about decisions, action items, requirements, or blockers →
  CALL `search_outcomes` with the matching `outcome_type` (one of
  "decision" | "action_item" | "requirement" | "blocker"). Pass an
  empty/omitted query when the user wants a list; FTS isn't needed if
  the filter is structural.
- "Last N meetings", "recent meetings" → CALL `list_recordings` first
  (it returns newest-first) to obtain the recording_ids, then pass them
  via `scope.recording_ids` to subsequent `search_*` calls.
- Person / project / dollar amount in the question → CALL `resolve_entity`
  first, then `list_recent_activity` or `search_transcripts` with the
  resolved label.
- Document references → `search_attachments`.
- Free-text topical questions → `search_transcripts` (+ `search_outcomes`
  in parallel if outcomes might exist).

NEVER conclude "no X exists" without at least one tool call that would
have surfaced X. If `search_outcomes(outcome_type="decision")` returns
zero items for the scoped recording_ids, only then is "no decisions"
defensible."""


SUBAGENT_SYSTEM_PROMPT = """You are a focused research sub-agent for Ghost.

You investigate ONE question scoped to a specific meeting or project and
return distilled findings + citations. Be terse:
- No preamble.
- Cite every claim (recording_id, segment_index, timestamp, speaker, etc.).
- 5-bullet maximum.
- If nothing relevant, return "(no evidence found)" and the tools you tried.

You do NOT spawn further sub-agents. You only use the core retrieval tools."""


def ask(
    question: str,
    *,
    conv_id: Optional[str] = None,
    project_id: Optional[str] = None,
    scope_hint: str = "cross_project",
    max_iterations: int = 8,
    on_event: Optional[Any] = None,
) -> dict[str, Any]:
    """Top-level Ghost entry point. Returns a dict with answer + citations
    + telemetry, also persists to ghost_messages.

    `on_event(event: dict)` is invoked synchronously for each tool start /
    tool done / triage / final event. Used by the streaming endpoint to
    surface activity to the UI in real time. Callbacks must not block.
    """
    settings = ghost_settings.get()
    if settings["mode"] != "hosted":
        raise RuntimeError("Local Ghost is not yet available; switch to hosted.")

    # Enforce monthly cap.
    cap = float(settings.get("monthly_cap_usd") or 0)
    if cap > 0:
        spent = ghost_convos.month_to_date_cost_usd()
        if spent >= cap:
            raise RuntimeError(
                f"Monthly cap reached (${spent:.2f} / ${cap:.2f}). "
                "Increase it in Settings → Ghost."
            )

    # Ensure conversation exists.
    if conv_id is None:
        conv = ghost_convos.create_conversation(title=question[:80], project_id=project_id)
        conv_id = conv["id"]
    else:
        if ghost_convos.get_conversation(conv_id) is None:
            raise ValueError(f"Conversation {conv_id} not found")

    ghost_convos.append_message(conv_id, "user", question)

    def _emit(kind: str, **data: Any) -> None:
        if on_event is None:
            return
        try:
            on_event({"kind": kind, **data})
        except Exception:
            logger.exception("on_event callback raised; ignoring")

    # Triage.
    t = triage_question(question, scope_hint=scope_hint)  # type: ignore[arg-type]
    tools = tools_for_intent(can_spawn_subagents=t.can_spawn_subagents)
    _emit("triage", intent=t.intent, scope=t.scope, can_spawn_subagents=t.can_spawn_subagents)

    llm = ghost_llm.get_llm()

    # Tool handler with sub-agent interception + event emission.
    def handler(name: str, args: dict[str, Any]) -> Any:
        _emit("tool.start", name=name, arguments=_summarize_args(name, args))
        try:
            if name == "spawn_research_subagents":
                from ghost.subagent import run_subagent_pool

                tasks = args.get("tasks", []) or []
                _emit("subagent.spawning", task_count=min(len(tasks), 6),
                      questions=[t.get("question", "")[:120] for t in tasks[:6]])
                result = run_subagent_pool(tasks, llm=llm, on_event=on_event)
                _emit("tool.done", name=name,
                      summary=f"{result.get('count', 0)} sub-agent finding(s)")
                return result
            fn = TOOL_HANDLERS.get(name)
            if fn is None:
                _emit("tool.done", name=name, summary="unknown tool", error=True)
                return {"error": f"Unknown tool: {name}"}
            result = fn(args)
            _emit("tool.done", name=name, summary=_summarize_result(name, result))
            return result
        except Exception as exc:
            _emit("tool.done", name=name, summary=str(exc), error=True)
            raise

    t0 = time.perf_counter()
    result = llm.run_tool_use_loop(
        system=SYSTEM_PROMPT,
        user=question,
        tools=tools,
        tool_handler=handler,
        max_iterations=max_iterations,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)

    citations = _extract_citations_from_tool_calls(result.tool_calls)
    cost = result.cost_usd()
    ghost_convos.append_message(
        conv_id,
        "assistant",
        result.answer,
        citations=citations,
        tool_calls=[_tool_call_to_dict(tc) for tc in result.tool_calls],
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=cost,
        latency_ms=latency_ms,
    )

    payload = {
        "conv_id": conv_id,
        "answer": result.answer,
        "citations": citations,
        "triage": t.__dict__,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": cost,
        "latency_ms": latency_ms,
        "tool_calls": [_tool_call_to_dict(tc) for tc in result.tool_calls],
    }
    _emit("final", **payload)
    return payload


def _summarize_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Produce a small, human-friendly snapshot of tool arguments for the UI."""
    out: dict[str, Any] = {}
    for k in ("query", "name", "kind", "entity_id", "recording_id", "speaker", "outcome_type"):
        if k in args and args[k] not in (None, ""):
            out[k] = args[k]
    scope = args.get("scope") or {}
    if isinstance(scope, dict):
        if scope.get("recording_ids"):
            out["recordings"] = len(scope["recording_ids"])
        if scope.get("project_ids"):
            out["projects"] = len(scope["project_ids"])
    return out


def _summarize_result(name: str, result: Any) -> str:
    """One-line summary of a tool result for the activity log."""
    if not isinstance(result, dict):
        return ""
    if "items" in result:
        return f"{len(result['items'])} hit(s)"
    if "candidates" in result:
        return f"{len(result['candidates'])} candidate(s)"
    if name == "get_recording_summary":
        return result.get("meeting_title") or result.get("title") or ""
    if name == "get_transcript_window":
        return f"{result.get('count', 0)} segment(s)"
    return ""


def _extract_citations_from_tool_calls(tool_calls) -> list[dict[str, Any]]:
    """Pull explicit citation fields out of tool results so the frontend
    can render clickable links. Conservative -- we surface what the
    retriever returned, not what the LLM claims."""
    cites: list[dict[str, Any]] = []
    seen = set()
    for tc in tool_calls:
        if not isinstance(tc.result, dict):
            continue
        items = tc.result.get("items") or []
        for it in items:
            st = it.get("source_type")
            if st == "segment":
                key = ("segment", it.get("recording_id"), it.get("segment_index"))
            elif st == "outcome":
                key = ("outcome", it.get("outcome_id"))
            elif st == "attachment":
                key = ("attachment", it.get("attachment_id"), it.get("chunk_index"))
            else:
                continue
            if key in seen:
                continue
            seen.add(key)
            cites.append(it)
    return cites


def _tool_call_to_dict(tc) -> dict[str, Any]:
    return {
        "name": tc.name,
        "arguments": tc.arguments,
        "arguments_summary": _summarize_args(tc.name, tc.arguments),
        "summary": _summarize_result(tc.name, tc.result),
        "result_preview": _preview(tc.result),
        "error": tc.error,
    }


def _preview(value: Any, max_len: int = 400) -> Any:
    """Truncate large tool results for storage. Full results stay in the
    in-flight tool transcript that the LLM sees; only the persisted preview
    is truncated."""
    if isinstance(value, dict):
        if "items" in value and isinstance(value["items"], list):
            return {"item_count": len(value["items"]), "first": value["items"][:2]}
        return value
    s = str(value)
    return s if len(s) <= max_len else (s[:max_len] + "...[truncated]")
