"""Integration tests for health, upload, and status endpoints."""

import uuid

import httpx
import pytest
from httpx import ASGITransport

from main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """GET /health returns 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_upload_recording(client, sample_audio):
    """POST /recordings with WAV file returns 201 with valid UUID id."""
    with open(sample_audio, "rb") as f:
        response = await client.post(
            "/recordings",
            files={"file": ("test.wav", f, "audio/wav")},
        )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    # Verify it's a valid UUID
    uuid.UUID(data["id"])


@pytest.mark.asyncio
async def test_upload_invalid_format(client):
    """POST /recordings with .txt file returns 400."""
    response = await client.post(
        "/recordings",
        files={"file": ("test.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_status_pending(client, sample_audio):
    """Upload then immediately check status -- should be pending."""
    with open(sample_audio, "rb") as f:
        upload_response = await client.post(
            "/recordings",
            files={"file": ("test.wav", f, "audio/wav")},
        )
    job_id = upload_response.json()["id"]

    status_response = await client.get(f"/recordings/{job_id}/status")
    assert status_response.status_code == 200
    # Job should still be pending (worker processes asynchronously)
    assert status_response.json()["status"] in ("pending", "processing")


@pytest.mark.asyncio
async def test_get_status_not_found(client):
    """GET /recordings/nonexistent/status returns 404."""
    response = await client.get("/recordings/nonexistent-id/status")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_transcript_not_ready(client, sample_audio):
    """Upload then immediately GET transcript -- should be 400."""
    with open(sample_audio, "rb") as f:
        upload_response = await client.post(
            "/recordings",
            files={"file": ("test.wav", f, "audio/wav")},
        )
    job_id = upload_response.json()["id"]

    transcript_response = await client.get(f"/recordings/{job_id}/transcript")
    assert transcript_response.status_code == 400
