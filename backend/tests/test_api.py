"""Integration tests for health, upload, status, outcomes, and promotion endpoints."""

import uuid

import httpx
import pytest
from httpx import ASGITransport

import storage
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


# --- Helper to set up a job with completed extraction ---

SAMPLE_OUTCOMES = [
    {
        "id": "outcome-decision-1",
        "type": "decision",
        "title": "Use React",
        "detail": "Team decided on React.",
        "confidence": 0.95,
        "evidence_refs": [
            {
                "segment_index": 0,
                "speaker": "Speaker 1",
                "timestamp": 0.0,
                "text_snippet": "Let's use React.",
            }
        ],
        "promoted": False,
        "promoted_id": None,
    },
    {
        "id": "outcome-action-1",
        "type": "action_item",
        "title": "API integration",
        "detail": "Speaker 2 handles API by Friday.",
        "confidence": 0.90,
        "evidence_refs": [
            {
                "segment_index": 1,
                "speaker": "Speaker 2",
                "timestamp": 5.5,
                "text_snippet": "I'll do API by Friday.",
            }
        ],
        "promoted": False,
        "promoted_id": None,
    },
    {
        "id": "outcome-req-1",
        "type": "requirement",
        "title": "Offline support",
        "detail": "Must support offline mode.",
        "confidence": 0.75,
        "evidence_refs": [
            {
                "segment_index": 0,
                "speaker": "Speaker 1",
                "timestamp": 0.0,
            }
        ],
        "promoted": False,
        "promoted_id": None,
    },
    {
        "id": "outcome-blocker-1",
        "type": "blocker",
        "title": "CI broken",
        "detail": "CI pipeline is down.",
        "confidence": 0.92,
        "evidence_refs": [],
        "promoted": False,
        "promoted_id": None,
    },
]

SAMPLE_RESULT = {
    "id": "test-job-123",
    "duration": 20.0,
    "language": "en",
    "speakers": [],
    "segments": [
        {
            "start": 0.0,
            "end": 5.0,
            "text": "Let's use React.",
            "speaker": "Speaker 1",
            "confidence": 0.95,
        },
        {
            "start": 5.5,
            "end": 10.0,
            "text": "I'll do API by Friday.",
            "speaker": "Speaker 2",
            "confidence": 0.90,
        },
    ],
}


def _create_test_job_with_outcomes(job_id: str = "test-job-123"):
    """Insert a job with completed extraction and outcomes via storage API."""
    storage.create_job(job_id, "/fake/path.wav", "Sprint Planning.wav")
    storage.update_job(
        job_id,
        status="completed",
        result=SAMPLE_RESULT,
        extraction_status="completed",
        outcomes=SAMPLE_OUTCOMES,
    )
    return job_id


# --- Outcomes endpoint tests ---


@pytest.mark.asyncio
async def test_outcomes_endpoint(client):
    """GET /recordings/{id}/outcomes returns outcomes list."""
    job_id = _create_test_job_with_outcomes()
    response = await client.get(f"/recordings/{job_id}/outcomes")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["extraction_status"] == "completed"
    assert len(data["outcomes"]) == 4


@pytest.mark.asyncio
async def test_outcomes_not_found(client):
    """GET /recordings/nonexistent/outcomes returns 404."""
    response = await client.get("/recordings/nonexistent/outcomes")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_status_includes_extraction(client):
    """GET /recordings/{id}/status includes extraction_status field."""
    job_id = _create_test_job_with_outcomes()
    response = await client.get(f"/recordings/{job_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert "extraction_status" in data
    assert data["extraction_status"] == "completed"


# --- Promotion tests ---


@pytest.mark.asyncio
async def test_promote_action_item(client):
    """Promote an action_item outcome returns task with backlink."""
    job_id = _create_test_job_with_outcomes()
    # outcome index 1 is the action_item
    response = await client.post(
        f"/recordings/{job_id}/outcomes/1/promote"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "task"
    assert "id" in data
    uuid.UUID(data["id"])  # valid UUID
    assert "From:" in data["backlink"]
    assert "Speaker 2" in data["backlink"]

    # Verify outcome is marked promoted in storage
    job = storage.get_job(job_id)
    assert job["outcomes"][1]["promoted"] is True
    assert job["outcomes"][1]["promoted_id"] == data["id"]


@pytest.mark.asyncio
async def test_promote_requirement(client):
    """Promote a requirement outcome returns requirement type."""
    job_id = _create_test_job_with_outcomes()
    # outcome index 2 is the requirement
    response = await client.post(
        f"/recordings/{job_id}/outcomes/2/promote"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "requirement"
    assert "id" in data


@pytest.mark.asyncio
async def test_promote_already_promoted(client):
    """Attempt to promote same outcome twice returns 409."""
    job_id = _create_test_job_with_outcomes()
    # First promotion
    response1 = await client.post(
        f"/recordings/{job_id}/outcomes/1/promote"
    )
    assert response1.status_code == 200
    # Second promotion
    response2 = await client.post(
        f"/recordings/{job_id}/outcomes/1/promote"
    )
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_promote_decision_rejected(client):
    """Attempt to promote a decision returns 400."""
    job_id = _create_test_job_with_outcomes()
    # outcome index 0 is the decision
    response = await client.post(
        f"/recordings/{job_id}/outcomes/0/promote"
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_promote_blocker_rejected(client):
    """Attempt to promote a blocker returns 400."""
    job_id = _create_test_job_with_outcomes()
    # outcome index 3 is the blocker
    response = await client.post(
        f"/recordings/{job_id}/outcomes/3/promote"
    )
    assert response.status_code == 400


# --- Extract endpoint one-shot guard tests ---


@pytest.mark.asyncio
async def test_extract_one_shot_guard_completed(client):
    """POST /extract with extraction_status='completed' returns 409."""
    job_id = _create_test_job_with_outcomes()  # has extraction_status="completed"
    response = await client.post(f"/recordings/{job_id}/extract")
    assert response.status_code == 409
    assert "already triggered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_one_shot_guard_pending(client):
    """POST /extract with extraction_status='pending' returns 409."""
    job_id = _create_test_job_with_outcomes()
    storage.update_job(job_id, extraction_status="pending")
    response = await client.post(f"/recordings/{job_id}/extract")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_extract_one_shot_guard_processing(client):
    """POST /extract with extraction_status='processing' returns 409."""
    job_id = _create_test_job_with_outcomes()
    storage.update_job(job_id, extraction_status="processing")
    response = await client.post(f"/recordings/{job_id}/extract")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_extract_allows_when_none(client):
    """POST /extract with extraction_status='none' and status='completed' returns 202."""
    job_id = _create_test_job_with_outcomes()
    storage.update_job(job_id, extraction_status="none")
    response = await client.post(f"/recordings/{job_id}/extract")
    assert response.status_code == 202
    # Verify extraction_status changed to pending
    job = storage.get_job(job_id)
    assert job["extraction_status"] == "pending"


@pytest.mark.asyncio
async def test_extract_allows_when_failed(client):
    """POST /extract with extraction_status='failed' and status='completed' returns 202."""
    job_id = _create_test_job_with_outcomes()
    storage.update_job(job_id, extraction_status="failed")
    response = await client.post(f"/recordings/{job_id}/extract")
    assert response.status_code == 202
    job = storage.get_job(job_id)
    assert job["extraction_status"] == "pending"


@pytest.mark.asyncio
async def test_extract_rejects_incomplete_stt(client):
    """POST /extract with status!='completed' returns 400."""
    storage.create_job("incomplete-job", "/fake.wav", "test.wav")
    response = await client.post("/recordings/incomplete-job/extract")
    assert response.status_code == 400


# --- Delete endpoint tests ---


@pytest.mark.asyncio
async def test_delete_recording(client):
    """DELETE /recordings/{id} removes the job."""
    job_id = _create_test_job_with_outcomes()
    response = await client.delete(f"/recordings/{job_id}")
    assert response.status_code == 204
    assert storage.get_job(job_id) is None


@pytest.mark.asyncio
async def test_delete_recording_not_found(client):
    """DELETE /recordings/nonexistent returns 404."""
    response = await client.delete("/recordings/nonexistent")
    assert response.status_code == 404
