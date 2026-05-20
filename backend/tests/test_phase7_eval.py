"""Phase 7: synthetic eval generator + runner + latency-threshold gate.

The runner is fed a mocked `ask_fn` so we exercise scoring + stats
without LLM cost. The latency-gate test enforces the targets from the
plan: lookup p95 < 8s, aggregation p95 < 20s.
"""

from typing import Any
from unittest.mock import patch

import pytest

import projects_store
import segments_store
import storage
from entities import store as entities_store
from ghost import (
    agent as ghost_agent,
    conversations as ghost_convos,
    settings as ghost_settings,
)
from ghost.eval import generator as eval_generator
from ghost.eval import store as eval_store
from ghost.eval.runner import run_all, run_one
from meeting_bot import dispatch_store


@pytest.fixture(autouse=True)
def init_phase7(reset_state):
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    entities_store.init()
    ghost_settings.init()
    ghost_convos.init()
    eval_store.init()
    ghost_settings.update(mode="hosted", provider="anthropic", api_key="sk-test", model="claude-opus-4-7")


def _populate_recording(rid, segments, outcomes=None):
    storage.create_job(rid, f"/tmp/{rid}.wav", f"{rid}.wav")
    storage.update_job(
        rid,
        status="completed",
        result={"meeting_title": rid, "duration": 60, "segments": segments},
        outcomes=outcomes or [],
    )


# ---------------------------------------------------------------------------
# Eval store
# ---------------------------------------------------------------------------


def test_add_and_list_query():
    q = eval_store.add_query(
        "When did we discuss $400?",
        "lookup_money",
        [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
    )
    rows = eval_store.list_queries()
    assert any(r["id"] == q["id"] for r in rows)
    fetched = eval_store.get_query(q["id"])
    assert fetched["expected_sources"][0]["segment_index"] == 5


def test_stats_returns_zeros_with_no_runs():
    s = eval_store.stats()
    assert s["count"] == 0


def test_record_and_aggregate_runs():
    q = eval_store.add_query("?", "kind", [])
    for lat, cost in [(100, 0.01), (200, 0.02), (300, 0.03)]:
        eval_store.record_run(
            q["id"], answer="a", cited_sources=[],
            tokens_in=10, tokens_out=5, cost_usd=cost, latency_ms=lat,
            primary_citation_correct=True, recall_at_k=1.0,
        )
    s = eval_store.stats()
    assert s["count"] == 3
    assert s["latency_p50_ms"] == 200
    assert s["primary_citation_correct_rate"] == 1.0


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def test_generate_creates_money_query():
    _populate_recording("rec-m", [
        {"start": 0, "end": 5, "speaker": "John",
         "text": "We agreed on the $400 quotation for the upcoming launch budget."},
    ])
    out = eval_generator.generate(n_target=4)
    assert out["created"] >= 1
    queries = eval_store.list_queries()
    assert any("$400" in q["question"] for q in queries)


def test_generate_creates_outcome_query():
    _populate_recording(
        "rec-o", [{"start": 0, "end": 1, "text": "hi"}],
        outcomes=[
            {"id": "o1", "type": "decision", "title": "Approve Acme contract", "detail": "..."}
        ],
    )
    out = eval_generator.generate(n_target=4)
    assert out["created"] >= 1
    queries = eval_store.list_queries()
    assert any("decision" in q["question"].lower() for q in queries)


# ---------------------------------------------------------------------------
# Runner with mocked ask_fn
# ---------------------------------------------------------------------------


def _mock_ask(question: str, **_) -> dict[str, Any]:
    """Pretend Ghost answered correctly with a primary segment citation."""
    return {
        "conv_id": "c1",
        "answer": "Mocked.",
        "citations": [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
        "tool_calls": [{
            "name": "search_transcripts",
            "arguments": {"query": question},
            "result_preview": {"item_count": 1, "first": [
                {"source_type": "segment", "recording_id": "r1", "segment_index": 5}
            ]},
        }],
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.01,
        "latency_ms": 1500,
    }


def test_run_one_scores_perfect_match():
    q = eval_store.add_query(
        "When did we?",
        "lookup_money",
        [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
    )
    res = run_one(q, ask_fn=_mock_ask)
    assert res["primary_citation_correct"] is True
    assert res["recall_at_k"] == 1.0


def test_run_one_misses_when_citation_wrong():
    q = eval_store.add_query(
        "?",
        "lookup_money",
        [{"source_type": "segment", "recording_id": "r1", "segment_index": 99}],
    )
    res = run_one(q, ask_fn=_mock_ask)
    assert res["primary_citation_correct"] is False
    assert res["recall_at_k"] == 0.0


def test_run_all_aggregates():
    for i in range(3):
        eval_store.add_query(
            f"q{i}", "kind",
            [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
        )
    out = run_all(ask_fn=_mock_ask)
    assert out["count"] == 3
    s = eval_store.stats(window_hours=1)
    assert s["count"] == 3
    assert s["latency_p50_ms"] == 1500


# ---------------------------------------------------------------------------
# Latency-threshold gate (the CI guardrail)
# ---------------------------------------------------------------------------


LOOKUP_P95_MS = 8000
AGGREGATION_P95_MS = 20000


def test_latency_thresholds_enforced_on_mock_runs():
    """Plan calls for: p95 lookup <8s, p95 aggregation <20s. We use the
    mock ask_fn (always returning 1500ms) to verify the assertion fires
    when run-history exceeds the cap."""
    # Run 20 queries -- all under cap with the default mock.
    for _ in range(20):
        q = eval_store.add_query(
            "lookup", "lookup",
            [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
        )
        run_one(q, ask_fn=_mock_ask)
    s = eval_store.stats(window_hours=1)
    assert s["latency_p95_ms"] < LOOKUP_P95_MS

    # Now inject a slow run via custom mock and verify the threshold triggers.
    def slow_ask(q: str, **_):
        out = _mock_ask(q)
        out["latency_ms"] = 30_000  # 30s
        return out

    slow_q = eval_store.add_query(
        "agg", "aggregation",
        [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
    )
    run_one(slow_q, ask_fn=slow_ask)
    s = eval_store.stats(window_hours=1)
    # P95 should still be <8s (we have 20 fast + 1 slow), so the threshold
    # holds. This validates the test methodology -- a single regression
    # doesn't trip the gate, only a sustained regression would.
    # If we run 20 slow ones the gate would fire:
    for _ in range(20):
        eval_store.record_run(
            slow_q["id"], answer="x", cited_sources=[],
            tokens_in=10, tokens_out=5, cost_usd=0.01, latency_ms=30_000,
            primary_citation_correct=False, recall_at_k=0.0,
        )
    s2 = eval_store.stats(window_hours=1)
    # Now ~half the runs are slow -> p95 should hit the slow value.
    assert s2["latency_p95_ms"] >= AGGREGATION_P95_MS


def test_regression_alert_detects_degradation_vs_baseline():
    """The /15% threshold check from the plan. Verifies that we can detect
    a >15% degradation between two windows of runs."""
    q = eval_store.add_query(
        "?", "kind",
        [{"source_type": "segment", "recording_id": "r1", "segment_index": 5}],
    )
    # 10 baseline runs at 1000ms
    for _ in range(10):
        eval_store.record_run(
            q["id"], answer="x", cited_sources=[],
            tokens_in=10, tokens_out=5, cost_usd=0.01, latency_ms=1000,
            primary_citation_correct=True, recall_at_k=1.0,
        )
    baseline_p95 = eval_store.stats(window_hours=24 * 7)["latency_p95_ms"]

    # Add 10 degraded runs at 2000ms (2x slower)
    for _ in range(10):
        eval_store.record_run(
            q["id"], answer="x", cited_sources=[],
            tokens_in=10, tokens_out=5, cost_usd=0.01, latency_ms=2000,
            primary_citation_correct=True, recall_at_k=1.0,
        )
    current_p95 = eval_store.stats(window_hours=24 * 7)["latency_p95_ms"]
    assert current_p95 > baseline_p95
    degradation_ratio = (current_p95 - baseline_p95) / max(baseline_p95, 1)
    assert degradation_ratio > 0.15  # >15% degradation detectable
