"""Sub-agent pool: depth-1 parallel investigations.

Used when the main agent invokes `spawn_research_subagents`. Each task
runs a focused tool-use loop against the core tools only, with its own
context. We run them in a thread pool (each sub-agent makes blocking
HTTP calls to the provider).

Caps:
    - max 6 tasks per spawn (enforced by the tool schema)
    - max 5 tool calls per sub-agent (enforced via max_iterations)
    - distilled findings only -- raw retrieval evidence stays inside the
      sub-agent's context; this is the win over single-context agents.
"""

import concurrent.futures
import logging
from typing import Any

from ghost.tools import CORE_TOOLS, TOOL_HANDLERS

logger = logging.getLogger(__name__)

MAX_SUBAGENTS = 6
SUBAGENT_MAX_ITERATIONS = 5
SUBAGENT_MAX_TOKENS_OUT = 8000


def _run_one_subagent(llm, task: dict[str, Any]) -> dict[str, Any]:
    """Invoke the LLM with the sub-agent system prompt + a single task."""
    question = task.get("question", "")
    scope = task.get("scope") or {}

    # Build the user message with explicit scope so the LLM can pass it
    # to its tool calls.
    user_msg = f"Investigation task: {question}"
    if scope:
        user_msg += f"\n\nDefault scope to use when calling tools: {scope}"

    def handler(name: str, args: dict[str, Any]) -> Any:
        # Default scope onto retrieval-style tool calls if not already set.
        if "scope" in args and not args["scope"] and scope:
            args = {**args, "scope": scope}
        elif scope and "scope" not in args:
            args = {**args, "scope": scope}
        fn = TOOL_HANDLERS.get(name)
        if fn is None:
            return {"error": f"Unknown tool: {name}"}
        return fn(args)

    from ghost.agent import SUBAGENT_SYSTEM_PROMPT

    result = llm.run_tool_use_loop(
        system=SUBAGENT_SYSTEM_PROMPT,
        user=user_msg,
        tools=CORE_TOOLS,
        tool_handler=handler,
        max_iterations=SUBAGENT_MAX_ITERATIONS,
    )
    return {
        "question": question,
        "scope": scope,
        "answer": result.answer,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "tool_count": len(result.tool_calls),
    }


def run_subagent_pool(
    tasks: list[dict[str, Any]], *, llm, on_event=None
) -> dict[str, Any]:
    """Run up to MAX_SUBAGENTS sub-agent investigations in parallel.

    Returns a dict summarizing each task's distilled answer. Raw retrieval
    evidence is NOT bubbled up -- the orchestrator only sees the findings.

    `on_event` is forwarded to the orchestrator's event stream so each
    sub-agent's question + completion show up in the live activity log.
    """
    if not tasks:
        return {"findings": [], "count": 0}
    tasks = tasks[:MAX_SUBAGENTS]
    findings: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), MAX_SUBAGENTS)) as ex:
        futures = {ex.submit(_run_one_subagent, llm, t): t for t in tasks}
        for fut in concurrent.futures.as_completed(futures):
            t = futures[fut]
            if on_event is not None:
                try:
                    on_event({"kind": "subagent.started", "question": t.get("question", "")[:120]})
                except Exception:
                    pass
            try:
                finding = fut.result()
                findings.append(finding)
                if on_event is not None:
                    try:
                        on_event({"kind": "subagent.done",
                                  "question": finding.get("question", "")[:120]})
                    except Exception:
                        pass
            except Exception as exc:
                logger.exception("subagent failed")
                findings.append({
                    "question": t.get("question", ""),
                    "scope": t.get("scope") or {},
                    "answer": f"(sub-agent failed: {exc})",
                    "tool_count": 0,
                })
                if on_event is not None:
                    try:
                        on_event({"kind": "subagent.done",
                                  "question": t.get("question", "")[:120],
                                  "error": str(exc)})
                    except Exception:
                        pass
    return {
        "findings": findings,
        "count": len(findings),
        "tokens_in_total": sum(f.get("tokens_in", 0) for f in findings),
        "tokens_out_total": sum(f.get("tokens_out", 0) for f in findings),
    }
