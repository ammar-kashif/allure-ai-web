"""Integration tests for the /meetings/* endpoints."""

import json

import httpx
import pytest
from httpx import ASGITransport

from main import app
from meeting_bot import dispatch_store
from meeting_bot.bot_client import BotClient
from meeting_bot.router import get_bot_client


@pytest.fixture(autouse=True)
def _init_dispatches():
    dispatch_store.init()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _bot_with(handler):
    """Build a BotClient that records dispatched payloads via MockTransport."""
    transport = httpx.MockTransport(handler)
    return BotClient(base_url="http://bot:3001", transport=transport)


@pytest.mark.asyncio
async def test_dispatch_creates_row_and_returns_recording_id(client):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(202, json={"status": "processing"})

    app.dependency_overrides[get_bot_client] = lambda: _bot_with(handler)
    try:
        response = await client.post(
            "/meetings/dispatch",
            json={
                "meeting_url": "https://meet.google.com/abc-defg-hij",
                "title": "Sprint review",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "dispatched"
    assert data["platform"] == "google"
    rec_id = data["recording_id"]
    assert len(rec_id) == 36  # uuid4

    # Bot received the correct shape.
    assert captured["path"] == "/google/join"
    assert captured["body"]["userId"] == rec_id
    assert captured["body"]["botId"] == rec_id
    assert captured["body"]["name"] == "Sprint review"

    # Row persisted with status='dispatched'.
    row = dispatch_store.get(rec_id)
    assert row is not None
    assert row["status"] == "dispatched"
    assert row["platform"] == "google"
    assert row["meeting_url"] == "https://meet.google.com/abc-defg-hij"
    assert row["title"] == "Sprint review"


@pytest.mark.asyncio
async def test_dispatch_infers_platform_from_zoom_url(client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={})

    app.dependency_overrides[get_bot_client] = lambda: _bot_with(handler)
    try:
        response = await client.post(
            "/meetings/dispatch",
            json={"meeting_url": "https://us04web.zoom.us/j/12345"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["platform"] == "zoom"


@pytest.mark.asyncio
async def test_dispatch_rejects_unknown_platform_url(client):
    response = await client.post(
        "/meetings/dispatch",
        json={"meeting_url": "https://webex.com/join/abc"},
    )
    assert response.status_code == 400
    assert "infer platform" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dispatch_returns_502_when_bot_rejects(client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="bot is on fire")

    app.dependency_overrides[get_bot_client] = lambda: _bot_with(handler)
    try:
        response = await client.post(
            "/meetings/dispatch",
            json={"meeting_url": "https://meet.google.com/x"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502

    # The dispatch row should be marked failed with the bot's error preserved.
    # Find it by listing all rows (we don't know the id; only one was created).
    import sqlite3

    import storage

    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM dispatches").fetchall()]
    conn.row_factory = None
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "500" in rows[0]["error"]


@pytest.mark.asyncio
async def test_dispatch_validates_empty_meeting_url(client):
    response = await client.post("/meetings/dispatch", json={"meeting_url": ""})
    assert response.status_code == 422  # Pydantic min_length


@pytest.mark.asyncio
async def test_get_meeting_status_returns_row(client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={})

    app.dependency_overrides[get_bot_client] = lambda: _bot_with(handler)
    try:
        post = await client.post(
            "/meetings/dispatch",
            json={"meeting_url": "https://meet.google.com/x"},
        )
        rec_id = post.json()["recording_id"]
        get = await client.get(f"/meetings/{rec_id}")
    finally:
        app.dependency_overrides.clear()

    assert get.status_code == 200
    body = get.json()
    assert body["recording_id"] == rec_id
    assert body["status"] == "dispatched"
    assert body["platform"] == "google"


@pytest.mark.asyncio
async def test_get_meeting_status_404_for_unknown(client):
    response = await client.get("/meetings/does-not-exist")
    assert response.status_code == 404
