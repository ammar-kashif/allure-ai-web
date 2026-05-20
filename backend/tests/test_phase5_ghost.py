"""Phase 5: Ghost agent + tools + triage + settings + conversations.

LLM is fully mocked via a FakeGhostLLM so tests don't make network calls
or require API keys. The tool dispatch + tool-use loop semantics are
covered by exercising the agent with scripted tool-use plans.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional
from unittest.mock import patch

import pytest

import projects_store
import segments_store
import storage
from entities import store as entities_store
from ghost import (
    agent as ghost_agent,
    conversations as ghost_convos,
    llm as ghost_llm,
    settings as ghost_settings,
    tools as ghost_tools,
)
from ghost.subagent import run_subagent_pool
from ghost.triage import triage
from meeting_bot import dispatch_store


@pytest.fixture(autouse=True)
def init_phase5(reset_state, monkeypatch):
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    entities_store.init()
    ghost_settings.init()
    ghost_convos.init()
    # Configure hosted Ghost with a fake key so get_llm() returns ours.
    ghost_settings.update(mode="hosted", provider="anthropic", api_key="sk-test", model="claude-opus-4-7")


# ---------------------------------------------------------------------------
# Settings + cost
# ---------------------------------------------------------------------------


def test_settings_default_hosted():
    # The fixture sets these; verify the round-trip.
    s = ghost_settings.get()
    assert s["mode"] == "hosted"
    assert s["provider"] == "anthropic"
    assert s["api_key_set"] is True


def test_settings_rejects_local_mode():
    with pytest.raises(ValueError):
        ghost_settings.update(mode="local")


def test_settings_clears_api_key_on_empty():
    ghost_settings.update(api_key="")
    s = ghost_settings.get()
    assert s["api_key_set"] is False


def test_estimate_cost_usd_known_model():
    cost = ghost_llm.estimate_cost_usd("claude-opus-4-7", tokens_in=1000, tokens_out=500)
    # 1k * 0.015 + 0.5k * 0.075 = 0.015 + 0.0375 = 0.0525
    assert 0.05 < cost < 0.06


def test_estimate_cost_usd_unknown_model_uses_default():
    cost = ghost_llm.estimate_cost_usd("never-heard-of", 1000, 1000)
    assert cost > 0


# ---------------------------------------------------------------------------
# Triage
# ---------------------------------------------------------------------------


def test_triage_aggregation_unlocks_subagents():
    t = triage("Summarize all blockers across projects")
    assert t.intent == "aggregation"
    assert t.can_spawn_subagents is True


def test_triage_lookup_blocks_subagents():
    t = triage("When did we discuss the $400 quotation with John?")
    assert t.intent == "lookup"
    assert t.can_spawn_subagents is False


def test_triage_navigation():
    t = triage("Show me the recording where we agreed on the pricing")
    assert t.intent == "navigation"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def test_resolve_entity_returns_candidates():
    entities_store.create_entity("person", "Jason Wu", aliases=["Jason"])
    out = ghost_tools.resolve_entity("Jason")
    assert out["candidates"]
    assert out["candidates"][0]["canonical_name"] == "Jason Wu"


def test_tools_for_intent_excludes_subagent_when_blocked():
    cor = ghost_tools.tools_for_intent(can_spawn_subagents=False)
    names = {t["name"] for t in cor}
    assert "spawn_research_subagents" not in names

    with_sub = ghost_tools.tools_for_intent(can_spawn_subagents=True)
    names = {t["name"] for t in with_sub}
    assert "spawn_research_subagents" in names


def test_search_transcripts_via_tool_handler():
    storage.create_job("rec-t", "/tmp/x.wav", "x.wav")
    storage.update_job("rec-t", status="completed", result={"segments": [
        {"start": 0, "end": 1, "speaker": "John", "text": "We agreed on $400."},
    ]})
    out = ghost_tools.TOOL_HANDLERS["search_transcripts"]({"query": "$400"})
    assert out["count"] >= 1
    assert out["items"][0]["recording_id"] == "rec-t"


def test_get_transcript_window_via_tool_handler():
    storage.create_job("rec-w", "/tmp/x.wav", "x.wav")
    storage.update_job("rec-w", status="completed", result={"segments": [
        {"start": 0, "end": 2, "text": "a"},
        {"start": 2, "end": 4, "text": "b"},
        {"start": 4, "end": 6, "text": "c"},
    ]})
    out = ghost_tools.TOOL_HANDLERS["get_transcript_window"]({
        "recording_id": "rec-w", "t_start": 1.0, "t_end": 5.0
    })
    assert out["count"] == 3  # all three overlap [1,5]


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def test_conversation_lifecycle():
    c = ghost_convos.create_conversation(title="test")
    ghost_convos.append_message(c["id"], "user", "Hello")
    ghost_convos.append_message(
        c["id"], "assistant", "Hi back",
        citations=[{"source_type": "segment", "recording_id": "r", "segment_index": 0}],
        tool_calls=[{"name": "resolve_entity", "arguments": {"name": "x"}}],
        tokens_in=10, tokens_out=5, cost_usd=0.0012, latency_ms=400,
    )
    msgs = ghost_convos.list_messages(c["id"])
    assert len(msgs) == 2
    assert msgs[1]["citations"]
    assert msgs[1]["cost_usd"] == pytest.approx(0.0012)


def test_month_to_date_cost_aggregates():
    c = ghost_convos.create_conversation()
    ghost_convos.append_message(c["id"], "assistant", "a", cost_usd=0.1)
    ghost_convos.append_message(c["id"], "assistant", "b", cost_usd=0.25)
    assert ghost_convos.month_to_date_cost_usd() == pytest.approx(0.35)


# ---------------------------------------------------------------------------
# Agent end-to-end (with FakeGhostLLM)
# ---------------------------------------------------------------------------


@dataclass
class FakeToolCall:
    name: str
    arguments: dict
    result: Any = None
    error: Optional[str] = None


class FakeGhostLLM(ghost_llm.GhostLLM):
    """Scripted LLM: a list of (kind, payload) steps. Each step is either
    ('tool', tool_name, arguments) or ('answer', text)."""

    name = "fake"

    def __init__(self, *, script: list[tuple], model: str = "claude-opus-4-7"):
        super().__init__(api_key="fake", model=model)
        self.script = script

    def run_tool_use_loop(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], Any],
        max_iterations: int = 8,
    ):
        calls: list[ghost_llm.ToolCall] = []
        tokens_in = 0
        tokens_out = 0
        steps = list(self.script)
        while steps:
            kind, *rest = steps.pop(0)
            tokens_in += 100
            if kind == "tool":
                name, args = rest
                tc = ghost_llm.ToolCall(name=name, arguments=args)
                try:
                    tc.result = tool_handler(name, args)
                except Exception as exc:
                    tc.error = str(exc)
                    tc.result = {"error": str(exc)}
                calls.append(tc)
                tokens_out += 50
                continue
            if kind == "answer":
                tokens_out += 100
                return ghost_llm.LoopResult(
                    answer=rest[0],
                    tool_calls=calls,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=self.model,
                )
            raise ValueError(f"Unknown script step kind: {kind!r}")
        # Fell off the end.
        return ghost_llm.LoopResult(
            answer="(script exhausted)",
            tool_calls=calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
        )


def _populate_recording(rid, segments):
    storage.create_job(rid, f"/tmp/{rid}.wav", f"{rid}.wav")
    storage.update_job(rid, status="completed", result={"segments": segments})


def test_agent_ask_runs_tool_then_answers(monkeypatch):
    _populate_recording("rec-q", [
        {"start": 30, "end": 35, "speaker": "John", "text": "Quote was $400 flat."},
    ])

    script = [
        ("tool", "search_transcripts", {"query": "$400"}),
        ("answer", "Quote was $400 flat. [rec: rec-q, 0:30, John]"),
    ]
    fake_llm = FakeGhostLLM(script=script)
    with patch.object(ghost_llm, "get_llm", return_value=fake_llm):
        result = ghost_agent.ask("When did we discuss the $400 quote?")
    assert result["answer"].startswith("Quote was $400")
    assert result["citations"]
    assert result["citations"][0]["recording_id"] == "rec-q"
    assert result["tokens_in"] > 0
    assert result["cost_usd"] >= 0


def test_agent_persists_messages():
    _populate_recording("rec-p", [{"start": 0, "end": 1, "text": "hello"}])
    script = [("answer", "hello back")]
    fake_llm = FakeGhostLLM(script=script)
    with patch.object(ghost_llm, "get_llm", return_value=fake_llm):
        result = ghost_agent.ask("hi")
    conv = ghost_convos.get_conversation(result["conv_id"])
    assert conv is not None
    msgs = ghost_convos.list_messages(result["conv_id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["cost_usd"] is not None


def test_agent_enforces_monthly_cap():
    # Set a tiny cap and stuff in fake history past it.
    ghost_settings.update(monthly_cap_usd=0.01)
    c = ghost_convos.create_conversation()
    ghost_convos.append_message(c["id"], "assistant", "burned", cost_usd=1.0)
    fake_llm = FakeGhostLLM(script=[("answer", "should never get here")])
    with patch.object(ghost_llm, "get_llm", return_value=fake_llm):
        with pytest.raises(RuntimeError, match="Monthly cap"):
            ghost_agent.ask("hello")


def test_subagent_pool_caps_at_max(monkeypatch):
    """spawn_research_subagents shouldn't run more than MAX_SUBAGENTS tasks."""
    calls = {"n": 0}

    def fake_one(llm, task):
        calls["n"] += 1
        return {
            "question": task["question"], "scope": task.get("scope") or {},
            "answer": "...", "tool_count": 0,
        }

    with patch("ghost.subagent._run_one_subagent", side_effect=fake_one):
        tasks = [{"question": f"q{i}"} for i in range(10)]
        out = run_subagent_pool(tasks, llm=object())
    assert calls["n"] == 6  # MAX_SUBAGENTS
    assert out["count"] == 6


def test_agent_subagent_escalation_path():
    """spawn_research_subagents fires when the LLM chooses to."""
    script = [
        ("tool", "spawn_research_subagents", {
            "tasks": [{"question": "what's up with project A"}, {"question": "and project B"}]
        }),
        ("answer", "Summary based on sub-agent findings"),
    ]
    fake_llm = FakeGhostLLM(script=script)

    # Each sub-agent itself runs the same fake_llm — give it a trivial script
    # by patching run_tool_use_loop to return a canned result.
    def fake_loop(**_):
        return ghost_llm.LoopResult(
            answer="(no evidence found)",
            tool_calls=[],
            tokens_in=20,
            tokens_out=10,
            model="fake",
        )
    fake_llm.run_tool_use_loop_orig = fake_llm.run_tool_use_loop  # type: ignore[attr-defined]

    with patch.object(ghost_llm, "get_llm", return_value=fake_llm):
        # Patch the sub-agent's per-task loop to use fake_loop instead.
        with patch("ghost.subagent._run_one_subagent",
                   side_effect=lambda llm, task: {
                       "question": task["question"], "scope": task.get("scope") or {},
                       "answer": "(no evidence found)", "tool_count": 0,
                   }):
            result = ghost_agent.ask(
                "Summarize all blockers across projects",
            )
    # Verify the agent's main loop saw the spawn call.
    tool_names = [tc["name"] for tc in result["tool_calls"]]
    assert "spawn_research_subagents" in tool_names
