"""Per-proposal verifier critic call.

Same submit-tool pattern as the detector, but with a tiny output schema
({vote, reason}). Skip if hypothetical / no clear owner / unsupported /
restates tracked work.
"""

from __future__ import annotations

from typing import Any

from ghost.llm import LoopResult, estimate_cost_usd

from .prompts import VERIFY_SYSTEM_PROMPT


SUBMIT_VOTE_TOOL: dict[str, Any] = {
    "name": "submit_vote",
    "description": "Vote on whether to ship or skip the proposed new task.",
    "parameters": {
        "type": "object",
        "required": ["vote", "reason"],
        "properties": {
            "vote": {"type": "string", "enum": ["ship", "skip"]},
            "reason": {"type": "string"},
        },
    },
}


def _format_proposal_prompt(
    proposal: dict[str, Any],
    transcript_window: str,
    open_tasks: list[dict[str, Any]],
) -> str:
    parts = [
        "## Proposed new task",
        f"title: {proposal.get('title','')}",
        f"owner_name: {proposal.get('owner_name','')}",
        f"verb_phrase: {proposal.get('verb_phrase','')}",
        f"reason: {proposal.get('reason','')}",
        f"source_segment_index: {proposal.get('source_segment_index','?')}",
        "",
        "## Transcript window (the source segment ± neighbors)",
        transcript_window or "(empty)",
        "",
        "## Open + recent tasks in this project (for duplicate check)",
    ]
    if open_tasks:
        for t in open_tasks[:30]:
            parts.append(f"- id={t['id']} title=\"{t.get('title','')}\" status={t.get('status','?')}")
    else:
        parts.append("(none)")
    return "\n".join(parts)


def get_transcript_window(
    segments: list[dict[str, Any]],
    center_idx: int,
    radius: int = 4,
) -> str:
    """Return ±radius segments around center_idx as a formatted block."""
    if not segments:
        return ""
    lo = max(0, center_idx - radius)
    hi = min(len(segments), center_idx + radius + 1)
    lines = []
    for i in range(lo, hi):
        seg = segments[i]
        ts = float(seg.get("start", 0.0))
        m = int(ts) // 60
        s = int(ts) % 60
        speaker = seg.get("speaker", "?")
        text = (seg.get("text") or "").replace("\n", " ").strip()
        marker = ">>" if i == center_idx else "  "
        lines.append(f"{marker} [{i}] {m}:{s:02d} {speaker}: {text}")
    return "\n".join(lines)


def verify_proposal(
    proposal: dict[str, Any],
    segments: list[dict[str, Any]],
    open_tasks: list[dict[str, Any]],
    llm: Any,
) -> dict[str, Any]:
    """Run one verifier critic call. Returns:
        {
            "vote": "ship" | "skip",
            "reason": str,
            "tokens_in": int,
            "tokens_out": int,
            "cost_usd": float,
        }
    """
    captured: dict[str, Any] = {"vote": None, "reason": ""}

    def handler(name: str, args: dict[str, Any]) -> Any:
        if name == "submit_vote":
            captured["vote"] = args.get("vote")
            captured["reason"] = args.get("reason", "")
            return {"ok": True}
        return {"error": f"unknown tool: {name}"}

    idx = proposal.get("source_segment_index", 0)
    window = get_transcript_window(segments, int(idx) if isinstance(idx, int) else 0)
    user = _format_proposal_prompt(proposal, window, open_tasks)

    result: LoopResult = llm.run_tool_use_loop(
        system=VERIFY_SYSTEM_PROMPT,
        user=user,
        tools=[SUBMIT_VOTE_TOOL],
        tool_handler=handler,
        max_iterations=2,
    )

    # If the LLM didn't vote, fail safe = skip.
    vote = captured["vote"] or "skip"
    reason = captured["reason"] or "verifier produced no vote"
    cost = estimate_cost_usd(result.model, result.tokens_in, result.tokens_out)
    return {
        "vote": vote,
        "reason": reason,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": cost,
    }
