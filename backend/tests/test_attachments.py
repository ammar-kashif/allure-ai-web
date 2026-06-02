"""Tests for attachment storage CRUD and HTTP endpoint operations."""

import io

import httpx
import pytest
from httpx import ASGITransport

import storage
from main import app


class TestAttachmentCRUD:
    """Tests for create_attachment, list_attachments, delete_attachment, get_attachment."""

    def test_create_and_list(self):
        """create_attachment stores record retrievable by list_attachments."""
        storage.create_attachment(
            attachment_id="att-1",
            recording_id="rec-1",
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            extracted_text="Hello world",
        )
        attachments = storage.list_attachments("rec-1")
        assert len(attachments) == 1
        assert attachments[0]["id"] == "att-1"
        assert attachments[0]["filename"] == "test.pdf"
        assert attachments[0]["file_type"] == "pdf"
        assert attachments[0]["file_size"] == 1024

    def test_list_excludes_extracted_text(self):
        """list_attachments returns metadata without extracted_text field."""
        storage.create_attachment(
            attachment_id="att-2",
            recording_id="rec-2",
            filename="test.docx",
            file_type="docx",
            file_size=2048,
            extracted_text="Some extracted content",
        )
        attachments = storage.list_attachments("rec-2")
        assert len(attachments) == 1
        assert "extracted_text" not in attachments[0]

    def test_delete_returns_true(self):
        """delete_attachment removes the record and returns True."""
        storage.create_attachment(
            attachment_id="att-3",
            recording_id="rec-3",
            filename="test.txt",
            file_type="txt",
            file_size=512,
            extracted_text="text content",
        )
        assert storage.delete_attachment("att-3") is True
        assert storage.list_attachments("rec-3") == []

    def test_delete_nonexistent_returns_false(self):
        """delete_attachment on nonexistent ID returns False."""
        assert storage.delete_attachment("nonexistent") is False

    def test_list_unknown_recording_returns_empty(self):
        """list_attachments for unknown recording_id returns empty list."""
        attachments = storage.list_attachments("unknown-recording")
        assert attachments == []

    def test_get_attachment_includes_extracted_text(self):
        """get_attachment returns full record including extracted_text."""
        storage.create_attachment(
            attachment_id="att-4",
            recording_id="rec-4",
            filename="doc.pdf",
            file_type="pdf",
            file_size=4096,
            extracted_text="Full extracted text here",
            extraction_error=None,
        )
        att = storage.get_attachment("att-4")
        assert att is not None
        assert att["extracted_text"] == "Full extracted text here"
        assert att["extraction_error"] is None

    def test_get_attachment_nonexistent(self):
        """get_attachment on nonexistent ID returns None."""
        assert storage.get_attachment("nonexistent") is None

    def test_create_with_extraction_error(self):
        """create_attachment with extraction_error stores it correctly."""
        storage.create_attachment(
            attachment_id="att-5",
            recording_id="rec-5",
            filename="corrupt.pdf",
            file_type="pdf",
            file_size=100,
            extracted_text="",
            extraction_error="Failed to parse PDF",
        )
        att = storage.get_attachment("att-5")
        assert att["extracted_text"] == ""
        assert att["extraction_error"] == "Failed to parse PDF"


# --- HTTP Endpoint Tests ---


@pytest.fixture
async def client():
    """Create async test client (same pattern as test_api.py)."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_upload_attachment(client):
    """POST a .txt file returns 201 with attachment metadata."""
    content = b"Hello from upload test."
    response = await client.post(
        "/recordings/test-job/attachments",
        files={"file": ("notes.txt", content, "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "notes.txt"
    assert data["file_type"] == "txt"
    assert data["file_size"] == len(content)
    assert data["recording_id"] == "test-job"


@pytest.mark.asyncio
async def test_upload_size_limit(client):
    """POST a file >10MB returns 413."""
    large_content = b"x" * (10 * 1024 * 1024 + 1)
    response = await client.post(
        "/recordings/test-job/attachments",
        files={"file": ("big.txt", large_content, "text/plain")},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_unsupported_type(client):
    """POST a .xyz file returns 400."""
    response = await client.post(
        "/recordings/test-job/attachments",
        files={"file": ("data.xyz", b"some data", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_attachments_endpoint(client):
    """GET /recordings/{id}/attachments returns list without extracted_text."""
    # Upload a file first
    await client.post(
        "/recordings/test-job-list/attachments",
        files={"file": ("doc.txt", b"test content", "text/plain")},
    )
    response = await client.get("/recordings/test-job-list/attachments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Verify no extracted_text in list items
    for item in data:
        assert "extracted_text" not in item
        assert "id" in item
        assert "filename" in item


@pytest.mark.asyncio
async def test_delete_attachment_endpoint(client):
    """DELETE /recordings/{id}/attachments/{aid} removes record, returns 204."""
    # Upload
    upload_resp = await client.post(
        "/recordings/test-job-del/attachments",
        files={"file": ("todelete.txt", b"delete me", "text/plain")},
    )
    attachment_id = upload_resp.json()["id"]

    # Delete
    del_resp = await client.delete(
        f"/recordings/test-job-del/attachments/{attachment_id}"
    )
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = await client.get("/recordings/test-job-del/attachments")
    ids = [a["id"] for a in list_resp.json()]
    assert attachment_id not in ids


@pytest.mark.asyncio
async def test_get_attachment_text(client):
    """GET /recordings/{id}/attachments/{aid}/text returns extracted content."""
    known_content = b"Known content for text extraction test."
    upload_resp = await client.post(
        "/recordings/test-job-text/attachments",
        files={"file": ("known.txt", known_content, "text/plain")},
    )
    attachment_id = upload_resp.json()["id"]

    text_resp = await client.get(
        f"/recordings/test-job-text/attachments/{attachment_id}/text"
    )
    assert text_resp.status_code == 200
    data = text_resp.json()
    assert data["id"] == attachment_id
    assert "Known content for text extraction test." in data["extracted_text"]

