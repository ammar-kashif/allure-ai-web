"""Replay eval queries through Ghost and score the results.

Scoring:
    primary_citation_correct: did the top citation point to one of the
        expected sources?
    recall_at_k: what fraction of expected sources appear anywhere in the
        agent's tool-call results (any source returned by retrieval, not
        just what the LLM cited in prose)?
    latency_ms / cost_usd: from the agent's LoopResult.

The runner does NOT enforce thresholds itself -- those are enforced as
test assertions in tests/test_phase7_eval.py so failures are visible in
CI alongside everything else.
"""

import logging
from typing import Any

from ghost import agent as ghost_agent
from ghost.eval import store as eval_store

logger = logging.getLogger(__name__)


def _matches_expected(citation: dict[str, Any], expected: dict[str, Any]) -> bool:
    st = expected.get("source_type")
    if citation.get("source_type") != st:
        return False
    if st == "segment":
        return (
            citation.get("recording_id") == expected.get("recording_id")
            and citation.get("segment_index") == expected.get("segment_index")
        )
    if st == "outcome":
        # Allow either outcome_id match or recording match (sometimes outcome ids
        # diverge across re-extractions; recording_id is a robust fallback).
        if citation.get("outcome_id") and expected.get("outcome_id"):
            return citation.get("outcome_id") == expected.get("outcome_id")
        return citation.get("recording_id") == expected.get("recording_id")
    if st == "attachment":
        return citation.get("attachment_id") == expected.get("attachment_id")
    return False


def _collect_retrieved_sources_from_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool-call previews hold up to 2 items each (see ghost.agent._preview).
    For eval purposes we want the full retrieval result -- ask the agent's
    citation extractor to dedupe across the run."""
    out: list[dict[str, Any]] = []
    for tc in tool_calls:
        rp = tc.get("result_preview") or {}
        # When the preview was truncated, `first` holds up to 2 items.
        first = rp.get("first") if isinstance(rp, dict) else None
        if isinstance(first, list):
            out.extend(first)
    return out


def run_one(query: dict[str, Any], *, ask_fn=ghost_agent.ask) -> dict[str, Any]:
    """Replay a single query through Ghost. Returns the recorded metrics."""
    question = query["question"]
    expected = query["expected_sources"] or []

    result = ask_fn(question)
    cited = result.get("citations") or []
    tool_calls = result.get("tool_calls") or []

    # primary correct: does the FIRST citation match any expected source?
    primary_correct = False
    if cited and expected:
        primary_correct = any(_matches_expected(cited[0], e) for e in expected)

    # recall_at_k: at least one expected source appears in the union of
    # citations + previewed tool results.
    retrieved_pool = cited + _collect_retrieved_sources_from_tool_calls(tool_calls)
    if not expected:
        recall = 1.0
    else:
        hits = 0
        for e in expected:
            if any(_matches_expected(c, e) for c in retrieved_pool):
                hits += 1
        recall = hits / len(expected)

    eval_store.record_run(
        query["id"],
        answer=result.get("answer", ""),
        cited_sources=cited,
        tokens_in=int(result.get("tokens_in", 0) or 0),
        tokens_out=int(result.get("tokens_out", 0) or 0),
        cost_usd=float(result.get("cost_usd", 0.0) or 0.0),
        latency_ms=int(result.get("latency_ms", 0) or 0),
        primary_citation_correct=primary_correct,
        recall_at_k=recall,
    )
    return {
        "query_id": query["id"],
        "primary_citation_correct": primary_correct,
        "recall_at_k": recall,
        "latency_ms": int(result.get("latency_ms", 0) or 0),
        "cost_usd": float(result.get("cost_usd", 0.0) or 0.0),
    }


def run_all(limit: int = 100, *, ask_fn=ghost_agent.ask) -> dict[str, Any]:
    queries = eval_store.list_queries(limit=limit)
    runs = []
    for q in queries:
        try:
            runs.append(run_one(q, ask_fn=ask_fn))
        except Exception as exc:
            logger.exception("eval run failed for %s", q["id"])
            runs.append({"query_id": q["id"], "error": str(exc)})
    return {"count": len(runs), "runs": runs, "stats": eval_store.stats(window_hours=1)}
