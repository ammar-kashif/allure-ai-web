"""Tests for attachment storage CRUD operations."""

import pytest

import storage


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
