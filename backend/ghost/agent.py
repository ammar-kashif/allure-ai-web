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
amount. Use search_transcripts + search_outcomes for topical questions;
search_attachments for document references."""


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
) -> dict[str, Any]:
    """Top-level Ghost entry point. Returns a dict with answer + citations
    + telemetry, also persists to ghost_messages."""
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

    # Triage.
    t = triage_question(question, scope_hint=scope_hint)  # type: ignore[arg-type]
    tools = tools_for_intent(can_spawn_subagents=t.can_spawn_subagents)

    llm = ghost_llm.get_llm()

    # Tool handler with sub-agent interception.
    def handler(name: str, args: dict[str, Any]) -> Any:
        if name == "spawn_research_subagents":
            from ghost.subagent import run_subagent_pool

            tasks = args.get("tasks", []) or []
            return run_subagent_pool(tasks, llm=llm)
        fn = TOOL_HANDLERS.get(name)
        if fn is None:
            return {"error": f"Unknown tool: {name}"}
        return fn(args)

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

    return {
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
