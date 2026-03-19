"""Tests for document generation: context injection, truncation, prompt content, generation functions."""

from unittest.mock import MagicMock, patch

import pytest


class TestFormatOutcomes:
    def test_format_outcomes_produces_numbered_list(self):
        from document_generation import format_outcomes_for_generation

        outcomes = [
            {"type": "decision", "title": "Use React", "detail": "Frontend framework", "confidence": 0.95},
            {"type": "task", "title": "Setup CI", "detail": "GitHub Actions", "confidence": 0.80},
        ]
        result = format_outcomes_for_generation(outcomes)
        assert "1. [DECISION] Use React" in result
        assert "2. [TASK] Setup CI" in result
        assert "Detail: Frontend framework" in result
        assert "Confidence: 0.95" in result

    def test_format_outcomes_empty_list(self):
        from document_generation import format_outcomes_for_generation

        result = format_outcomes_for_generation([])
        assert result == ""


class TestBuildDocumentContext:
    @patch("document_generation.get_attachments_with_text")
    def test_no_attachments_returns_empty_string(self, mock_get):
        from document_generation import build_document_context

        mock_get.return_value = []
        result = build_document_context("rec-123")
        assert result == ""

    @patch("document_generation.get_attachments_with_text")
    def test_single_doc_returns_formatted_section(self, mock_get):
        from document_generation import build_document_context

        mock_get.return_value = [
            {"id": "a1", "filename": "spec.pdf", "extracted_text": "Product specification content here."},
        ]
        result = build_document_context("rec-123")
        assert "## Reference Documents" in result
        assert "### spec.pdf" in result
        assert "Product specification content here." in result

    @patch("document_generation.get_attachments_with_text")
    def test_multiple_docs_splits_budget_equally(self, mock_get):
        from document_generation import build_document_context

        doc1_text = "A" * 10000
        doc2_text = "B" * 10000
        mock_get.return_value = [
            {"id": "a1", "filename": "doc1.pdf", "extracted_text": doc1_text},
            {"id": "a2", "filename": "doc2.pdf", "extracted_text": doc2_text},
        ]
        # With max_chars=16000, each doc gets 8000 chars
        result = build_document_context("rec-123", max_chars=16000)
        # Both docs should be present
        assert "### doc1.pdf" in result
        assert "### doc2.pdf" in result
        # Each doc should be truncated to 8000 chars (budget is 16000 / 2 = 8000)
        # The truncated text should not contain the full 10000 chars
        assert "A" * 10000 not in result
        assert "B" * 10000 not in result
        assert "[truncated]" in result

    @patch("document_generation.get_attachments_with_text")
    def test_truncation_adds_marker_and_note(self, mock_get):
        from document_generation import build_document_context

        mock_get.return_value = [
            {"id": "a1", "filename": "big.pdf", "extracted_text": "X" * 500},
        ]
        result = build_document_context("rec-123", max_chars=100)
        assert "[truncated]" in result
        assert "truncated" in result.lower()
        # Header should include truncation note
        lines = result.split("\n")
        header_area = "\n".join(lines[:3])
        assert "truncated" in header_area.lower()

    @patch("document_generation.get_attachments_with_text")
    def test_empty_text_docs_filtered_out(self, mock_get):
        from document_generation import build_document_context

        mock_get.return_value = [
            {"id": "a1", "filename": "empty.pdf", "extracted_text": ""},
            {"id": "a2", "filename": "whitespace.pdf", "extracted_text": "   \n  "},
            {"id": "a3", "filename": "real.pdf", "extracted_text": "Real content here"},
        ]
        result = build_document_context("rec-123")
        assert "### real.pdf" in result
        assert "empty.pdf" not in result
        assert "whitespace.pdf" not in result

    @patch("document_generation.get_attachments_with_text")
    def test_single_doc_gets_full_budget(self, mock_get):
        from document_generation import build_document_context

        text = "A" * 200
        mock_get.return_value = [
            {"id": "a1", "filename": "doc.pdf", "extracted_text": text},
        ]
        result = build_document_context("rec-123", max_chars=200)
        # Should not be truncated since text fits the budget
        assert "[truncated]" not in result
        assert "A" * 200 in result

    @patch("document_generation.get_attachments_with_text")
    def test_two_docs_split_budget_50_50(self, mock_get):
        from document_generation import build_document_context

        mock_get.return_value = [
            {"id": "a1", "filename": "d1.pdf", "extracted_text": "A" * 100},
            {"id": "a2", "filename": "d2.pdf", "extracted_text": "B" * 100},
        ]
        # Budget of 200 split 2 ways = 100 each, text is exactly 100 so no truncation
        result = build_document_context("rec-123", max_chars=200)
        assert "[truncated]" not in result
