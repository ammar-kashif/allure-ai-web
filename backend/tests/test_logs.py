"""Tests for persisted operational logs."""

import httpx
import pytest
from httpx import ASGITransport

import log_store
import storage
from main import app
from meeting_bot import dispatch_store
from meeting_bot.bot_client import BotClient
from meeting_bot.router import get_bot_client
from observability import log_event, step_timer


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_log_store_records_and_filters_events():
    log_store.record_event(
        category="transcription",
        event="stt.completed",
        status="done",
        message="Transcription completed",
        job_id="job-1",
        duration_ms=123,
        metadata={"segments": 3},
    )
    log_store.record_event(
        category="bot",
        event="bot.waiting",
        status="start",
        dispatch_id="dispatch-1",
        recording_id="dispatch-1",
    )

    transcription_logs = log_store.list_events(category="transcription")
    assert len(transcription_logs) == 1
    assert transcription_logs[0]["event"] == "stt.completed"
    assert transcription_logs[0]["metadata"] == {"segments": 3}

    start_logs = log_store.list_events(status="start")
    assert len(start_logs) == 1
    assert start_logs[0]["dispatch_id"] == "dispatch-1"


def test_step_timer_persists_start_done_and_failed_events():
    with step_timer("stt.moonshine", job_id="job-1", n_segments=2):
        pass

    logs = log_store.list_events(job_id="job-1", category="transcription")
    statuses = [event["status"] for event in logs]
    assert "start" in statuses
    assert "done" in statuses
    assert any(event["duration_ms"] is not None for event in logs)

    with pytest.raises(ValueError):
        with step_timer("extraction.llm", job_id="job-2"):
            raise ValueError("bad json")

    failed = log_store.list_events(job_id="job-2", status="failed")
    assert len(failed) == 1
    assert failed[0]["level"] == "error"
    assert failed[0]["metadata"]["error"] == "bad json"


def test_observability_is_best_effort(monkeypatch):
    def boom(**_kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(log_store, "record_event", boom)

    log_event(
        category="pipeline",
        event="test.event",
        status="done",
        message="Should not raise",
    )


@pytest.mark.asyncio
async def test_logs_endpoint_filters_events(client):
    log_store.record_event(
        category="document",
        event="document.prd",
        status="done",
        job_id="job-1",
    )
    log_store.record_event(
        category="bot",
        event="bot.waiting",
        status="start",
        dispatch_id="dispatch-1",
    )

    response = await client.get("/logs?category=bot&status=start")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["event"] == "bot.waiting"


@pytest.mark.asyncio
async def test_bot_dispatch_and_stop_emit_logs(client):
    dispatch_store.init()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/jobs/stop":
            return httpx.Response(202, json={"ok": True})
        return httpx.Response(202, json={"status": "processing"})

    app.dependency_overrides[get_bot_client] = lambda: BotClient(
        base_url="http://bot:3001",
        transport=httpx.MockTransport(handler),
    )
    try:
        post = await client.post(
            "/meetings/dispatch",
            json={"meeting_url": "https://meet.google.com/abc-defg-hij"},
        )
        rec_id = post.json()["recording_id"]
        await client.post(f"/meetings/{rec_id}/stop")
    finally:
        app.dependency_overrides.clear()

    events = [event["event"] for event in log_store.list_events(category="bot")]
    assert "bot.waiting" in events
    assert "bot.dispatched" in events
    assert "bot.stop_requested" in events


@pytest.mark.asyncio
async def test_generate_prd_endpoint_emits_document_logs(client, monkeypatch):
    import document_generation

    monkeypatch.setattr(document_generation, "build_document_context", lambda job_id: "")
    monkeypatch.setattr(
        document_generation,
        "generate_prd",
        lambda job_id, app_state, document_context="": "PRD content",
    )

    storage.create_job("job-prd", "/fake/path.wav", "Planning.wav")
    storage.update_job(
        "job-prd",
        status="completed",
        result={"segments": []},
        outcomes=[
            {
                "id": "outcome-1",
                "type": "decision",
                "title": "Use React",
                "detail": "The team chose React.",
                "confidence": 0.9,
                "evidence_refs": [],
                "promoted": False,
                "promoted_id": None,
            }
        ],
    )

    response = await client.post("/recordings/job-prd/generate-prd")
    assert response.status_code == 200

    logs = log_store.list_events(category="document", job_id="job-prd")
    statuses = {event["status"] for event in logs if event["event"] == "document.prd"}
    assert statuses == {"start", "done"}
