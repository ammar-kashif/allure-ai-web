"""Phase 8: autonomous follow-up pass — store + runner + executor."""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

import projects_store
import segments_store
import storage
from autonomy import store as autonomy_store
from autonomy.runner import run_autonomy
from entities import store as entities_store
from ghost import (
    conversations as ghost_convos,
    settings as ghost_settings,
)
from meeting_bot import dispatch_store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def init_phase8(reset_state, tmp_path):
    dispatch_store.init()
    projects_store.init()
    segments_store.init()
    entities_store.init()
    ghost_settings.init()
    ghost_convos.init()
    autonomy_store.init()
    # Hosted Ghost configured with a stub key so get_llm() doesn't bail.
    ghost_settings.update(
        mode="hosted", provider="anthropic", api_key="sk-test", model="claude-opus-4-7"
    )

    # Stand up a minimal frontend SQLite at FRONTEND_DB_PATH so the
    # autonomy executor's task writes have somewhere to land.
    import frontend_sync as fs

    fdb = tmp_path / "frontend.db"
    fs.FRONTEND_DB_PATH = fdb  # type: ignore[assignment]
    conn = sqlite3.connect(str(fdb))
    conn.executescript(
        """
        CREATE TABLE recordings (
            id TEXT PRIMARY KEY,
            title TEXT,
            backend_id TEXT,
            project_id TEXT,
            file_path TEXT,
            status TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            detail TEXT DEFAULT '',
            source_outcome_id TEXT,
            source_recording_id TEXT,
            backlink TEXT,
            status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            assignee TEXT,
            tags TEXT DEFAULT '[]',
            autonomy_action_id TEXT,
            autonomy_run_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()
    yield


def _make_recording(
    job_id: str,
    project_id: str | None,
    duration: float,
    segments: list[dict[str, Any]],
    outcomes: list[dict[str, Any]] | None = None,
    *,
    is_follow_up: bool = False,
    unresolved_commitments: list[dict[str, Any]] | None = None,
):
    storage.create_job(job_id, f"/tmp/{job_id}.wav", f"{job_id}.wav")
    if project_id:
        conn = storage._get_conn()
        conn.execute(
            "UPDATE jobs SET project_id = ? WHERE id = ?",
            (project_id, job_id),
        )
        conn.commit()
    storage.update_job(
        job_id,
        status="completed",
        extraction_status="completed",
        result={
            "duration": duration,
            "segments": segments,
            "is_follow_up": is_follow_up,
            "is_retro": False,
            "referenced_prior_topics": [],
            "unresolved_commitments": unresolved_commitments or [],
        },
        outcomes=outcomes or [],
    )
    # Mirror to the test frontend DB so the join in list_project_tasks works.
    import frontend_sync as fs

    conn = sqlite3.connect(str(fs.FRONTEND_DB_PATH))
    conn.execute(
        "INSERT OR REPLACE INTO recordings (id, title, backend_id, project_id, status) "
        "VALUES (?, ?, ?, ?, 'ready')",
        (job_id, job_id, job_id, project_id),
    )
    conn.commit()
    conn.close()


# A FakeGhostLLM that lets us drive the submit-tool by canned payloads.
class FakeGhostLLM:
    def __init__(self, *, detect_payload=None, vote_sequence=None):
        self.detect_payload = detect_payload or {
            "task_matches": [],
            "proposed_new_tasks": [],
            "follow_up_to_recordings": [],
        }
        self.vote_sequence = list(vote_sequence or [])
        self.model = "claude-opus-4-7"

    def run_tool_use_loop(self, *, system, user, tools, tool_handler, max_iterations=8):
        from ghost.llm import LoopResult

        # Inspect which tool to call by the system prompt prefix.
        if "verifier" in (system or "").lower() or "submit_vote" in (tools[0]["name"] if tools else ""):
            vote = self.vote_sequence.pop(0) if self.vote_sequence else {"vote": "ship", "reason": "looks good"}
            tool_handler("submit_vote", vote)
        else:
            tool_handler("submit_findings", self.detect_payload)
        return LoopResult(
            answer="",
            tool_calls=[],
            tokens_in=100,
            tokens_out=50,
            model=self.model,
        )


# ---------------------------------------------------------------------------
# Store tests
# ---------------------------------------------------------------------------


def test_create_run_and_actions_update_counters():
    run = autonomy_store.create_run("rec1", "proj1")
    a1 = autonomy_store.add_action(run["id"], "rec1", "task_created")
    autonomy_store.add_action(run["id"], "rec1", "task_discussed")
    autonomy_store.add_action(run["id"], "rec1", "skipped_duplicate")
    final = autonomy_store.get_run(run["id"])
    assert final["tasks_created"] == 1
    assert final["tasks_discussed"] == 1
    # Reversing the created action drops the counter.
    autonomy_store.mark_action_reversed(a1["id"])
    final2 = autonomy_store.get_run(run["id"])
    assert final2["tasks_created"] == 0


def test_settings_round_trip():
    s = autonomy_store.get_settings()
    assert s["enabled"] is True
    autonomy_store.update_settings(enabled=False, monthly_cap_usd=42.0,
                                    disabled_project_ids=["p1", "p2"])
    s2 = autonomy_store.get_settings()
    assert s2["enabled"] is False
    assert s2["monthly_cap_usd"] == 42.0
    assert s2["disabled_project_ids"] == ["p1", "p2"]


# ---------------------------------------------------------------------------
# Skip paths
# ---------------------------------------------------------------------------


def test_skips_when_no_project():
    _make_recording("rec-np", None, 300.0, [{"start": 0, "end": 1, "text": "x"}])
    result = run_autonomy("rec-np", SimpleNamespace())
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "no_project"


def test_skips_when_first_in_project():
    _make_recording("rec-first", "proj-A", 300.0, [{"start": 0, "end": 1, "text": "x"}])
    result = run_autonomy("rec-first", SimpleNamespace())
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "first_in_project"


def test_skips_when_too_short():
    _make_recording("rec-prior", "proj-S", 600.0, [{"start": 0, "end": 1, "text": "y"}])
    _make_recording("rec-short", "proj-S", 60.0, [{"start": 0, "end": 1, "text": "x"}])
    result = run_autonomy("rec-short", SimpleNamespace())
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "too_short"


def test_skips_when_globally_disabled():
    autonomy_store.update_settings(enabled=False)
    _make_recording("rec-prior", "proj-D", 600.0, [{"start": 0, "end": 1, "text": "y"}])
    _make_recording("rec-d", "proj-D", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    result = run_autonomy("rec-d", SimpleNamespace())
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "disabled_global"


def test_skips_when_project_disabled():
    autonomy_store.update_settings(disabled_project_ids=["proj-X"])
    _make_recording("rec-prior", "proj-X", 600.0, [{"start": 0, "end": 1, "text": "y"}])
    _make_recording("rec-x", "proj-X", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    result = run_autonomy("rec-x", SimpleNamespace())
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "disabled_project"


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_happy_path_creates_task():
    _make_recording(
        "rec-prior", "proj-H", 600.0,
        [{"start": 0, "end": 5, "speaker": "Alice", "text": "we started Acme onboarding"}],
        outcomes=[{"id": "o1", "type": "decision", "title": "Begin Acme onboarding", "detail": "..."}],
    )
    _make_recording(
        "rec-h", "proj-H", 600.0,
        [
            {"start": 0, "end": 5, "speaker": "Jason", "text": "I'll draft the launch deck this week."},
            {"start": 5, "end": 10, "speaker": "Sarah", "text": "Sounds good."},
        ],
        is_follow_up=True,
    )
    fake_llm = FakeGhostLLM(
        detect_payload={
            "task_matches": [],
            "proposed_new_tasks": [
                {
                    "title": "Draft launch deck",
                    "owner_name": "Jason",
                    "source_segment_index": 0,
                    "verb_phrase": "will draft the launch deck",
                    "reason": "explicit commitment with owner",
                    "duplicate_of_task_id": None,
                }
            ],
            "follow_up_to_recordings": ["rec-prior"],
        },
        vote_sequence=[{"vote": "ship", "reason": "clear commitment"}],
    )
    with patch("ghost.llm.get_llm", return_value=fake_llm):
        result = run_autonomy("rec-h", SimpleNamespace())
    assert result["status"] == "completed"
    run = autonomy_store.get_run(result["run_id"])
    assert run["tasks_created"] == 1
    assert run["follow_up_to"] == ["rec-prior"]
    # Task landed in frontend DB
    import frontend_sync as fs

    conn = sqlite3.connect(str(fs.FRONTEND_DB_PATH))
    rows = conn.execute(
        "SELECT title, assignee, autonomy_action_id FROM tasks WHERE source_recording_id = ?",
        ("rec-h",),
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "Draft launch deck"
    assert rows[0][1] == "Jason"
    assert rows[0][2] is not None


def test_verifier_skip_blocks_creation():
    _make_recording("rec-prior", "proj-V", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    _make_recording(
        "rec-v", "proj-V", 600.0,
        [{"start": 0, "end": 5, "speaker": "?", "text": "maybe we could write a doc someday."}],
    )
    fake_llm = FakeGhostLLM(
        detect_payload={
            "task_matches": [],
            "proposed_new_tasks": [
                {
                    "title": "Write a doc",
                    "owner_name": "someone",
                    "source_segment_index": 0,
                    "verb_phrase": "could write",
                    "reason": "hedge",
                }
            ],
            "follow_up_to_recordings": [],
        },
        vote_sequence=[{"vote": "skip", "reason": "hypothetical, no clear owner"}],
    )
    with patch("ghost.llm.get_llm", return_value=fake_llm):
        result = run_autonomy("rec-v", SimpleNamespace())
    run = autonomy_store.get_run(result["run_id"])
    assert run["tasks_created"] == 0
    actions = autonomy_store.list_actions(result["run_id"])
    kinds = [a["kind"] for a in actions]
    assert "skipped_verifier" in kinds


def test_appears_done_marks_only_no_task_mutation():
    # Prior recording owns an open task we'll match against.
    _make_recording("rec-prior", "proj-D2", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    _make_recording("rec-d", "proj-D2", 600.0, [{"start": 0, "end": 5, "speaker": "Alex", "text": "Acme onboarding is shipped."}])
    # Seed an existing task linked to the prior recording so list_project_tasks
    # has something to surface.
    import frontend_sync as fs

    conn = sqlite3.connect(str(fs.FRONTEND_DB_PATH))
    conn.execute(
        "INSERT INTO tasks (id, title, source_recording_id, status, priority) "
        "VALUES ('t-known', 'Acme onboarding', 'rec-prior', 'todo', 'medium')"
    )
    conn.commit()
    conn.close()
    fake_llm = FakeGhostLLM(
        detect_payload={
            "task_matches": [
                {
                    "task_id": "t-known",
                    "action": "appears_done",
                    "evidence_segments": [0],
                    "reason": "explicitly shipped",
                }
            ],
            "proposed_new_tasks": [],
            "follow_up_to_recordings": [],
        },
    )
    with patch("ghost.llm.get_llm", return_value=fake_llm):
        result = run_autonomy("rec-d", SimpleNamespace())
    run = autonomy_store.get_run(result["run_id"])
    assert run["tasks_discussed"] == 1
    # The existing task is untouched (still 'todo').
    conn = sqlite3.connect(str(fs.FRONTEND_DB_PATH))
    status = conn.execute("SELECT status FROM tasks WHERE id = 't-known'").fetchone()[0]
    conn.close()
    assert status == "todo"


def test_undo_single_action_deletes_task():
    _make_recording("rec-prior", "proj-U", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    _make_recording(
        "rec-u", "proj-U", 600.0,
        [{"start": 0, "end": 5, "speaker": "Pat", "text": "I'll send the proposal Friday."}],
    )
    fake_llm = FakeGhostLLM(
        detect_payload={
            "task_matches": [],
            "proposed_new_tasks": [
                {
                    "title": "Send proposal",
                    "owner_name": "Pat",
                    "source_segment_index": 0,
                    "verb_phrase": "will send the proposal",
                    "reason": "explicit",
                }
            ],
            "follow_up_to_recordings": [],
        },
        vote_sequence=[{"vote": "ship", "reason": "ok"}],
    )
    with patch("ghost.llm.get_llm", return_value=fake_llm):
        result = run_autonomy("rec-u", SimpleNamespace())
    actions = autonomy_store.list_actions(result["run_id"])
    created = [a for a in actions if a["kind"] == "task_created"][0]
    # Now undo.
    from frontend_sync import delete_task_by_autonomy_action_id

    deleted = delete_task_by_autonomy_action_id(created["id"])
    autonomy_store.mark_action_reversed(created["id"])
    assert deleted == 1
    assert autonomy_store.get_action(created["id"])["reversed_at"] is not None
    # Run counter decremented.
    run = autonomy_store.get_run(result["run_id"])
    assert run["tasks_created"] == 0


def test_detector_unknown_task_id_emits_skipped_gate():
    _make_recording("rec-prior", "proj-UK", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    _make_recording(
        "rec-uk", "proj-UK", 600.0,
        [{"start": 0, "end": 5, "text": "Old work is done."}],
    )
    fake_llm = FakeGhostLLM(
        detect_payload={
            "task_matches": [
                {
                    "task_id": "ghost-task-id-that-doesnt-exist",
                    "action": "appears_done",
                    "evidence_segments": [0],
                    "reason": "hallucinated",
                }
            ],
            "proposed_new_tasks": [],
            "follow_up_to_recordings": [],
        },
    )
    with patch("ghost.llm.get_llm", return_value=fake_llm):
        result = run_autonomy("rec-uk", SimpleNamespace())
    actions = autonomy_store.list_actions(result["run_id"])
    assert any(a["kind"] == "skipped_gate" for a in actions)


def test_failed_run_status_when_llm_unavailable():
    _make_recording("rec-prior", "proj-F", 600.0, [{"start": 0, "end": 1, "text": "x"}])
    _make_recording("rec-f", "proj-F", 600.0, [{"start": 0, "end": 5, "text": "anything"}])
    # Force LLM to raise.
    def _raise():
        raise RuntimeError("API key missing")
    with patch("ghost.llm.get_llm", side_effect=_raise):
        result = run_autonomy("rec-f", SimpleNamespace())
    assert result["status"] == "failed"
    assert "API key" in result["error"]
