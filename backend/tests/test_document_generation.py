"""Tests for document generation: context injection, truncation, prompt content, generation functions, endpoint wiring."""

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
        result = build_document_context("rec-123", max_chars=16000)
        assert "### doc1.pdf" in result
        assert "### doc2.pdf" in result
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
        assert "[truncated]" not in result
        assert "A" * 200 in result

    @patch("document_generation.get_attachments_with_text")
    def test_two_docs_split_budget_50_50(self, mock_get):
        from document_generation import build_document_context

        mock_get.return_value = [
            {"id": "a1", "filename": "d1.pdf", "extracted_text": "A" * 100},
            {"id": "a2", "filename": "d2.pdf", "extracted_text": "B" * 100},
        ]
        result = build_document_context("rec-123", max_chars=200)
        assert "[truncated]" not in result


class TestPromptContent:
    """Validate prompt constants contain required content."""

    def test_prd_prompt_contains_standalone_product_spec(self):
        from document_generation import PRD_SYSTEM_PROMPT

        assert "standalone product spec" in PRD_SYSTEM_PROMPT.lower()

    def test_prd_prompt_does_not_reference_speakers(self):
        from document_generation import PRD_SYSTEM_PROMPT

        assert "Reference specific speakers" not in PRD_SYSTEM_PROMPT

    def test_prd_prompt_contains_all_six_sections(self):
        from document_generation import PRD_SYSTEM_PROMPT

        required_sections = [
            "Overview",
            "Goals",
            "Objectives",
            "Functional Requirements",
            "Non-Functional Requirements",
            "Constraints",
            "Open Questions",
        ]
        for section in required_sections:
            assert section in PRD_SYSTEM_PROMPT, f"Missing section: {section}"

    def test_prd_prompt_has_no_speaker_timestamp_instruction(self):
        from document_generation import PRD_SYSTEM_PROMPT

        assert "speakers and timestamps" not in PRD_SYSTEM_PROMPT.lower()
        assert "Do NOT reference speakers" in PRD_SYSTEM_PROMPT

    def test_diagram_prompt_handles_both_types(self):
        from document_generation import DIAGRAM_SYSTEM_PROMPT

        assert "ERD" in DIAGRAM_SYSTEM_PROMPT
        assert "Flowchart" in DIAGRAM_SYSTEM_PROMPT

    def test_diagram_prompt_outputs_only_mermaid(self):
        from document_generation import DIAGRAM_SYSTEM_PROMPT

        assert "Mermaid code only" in DIAGRAM_SYSTEM_PROMPT

    def test_diagram_prompt_no_fences(self):
        from document_generation import DIAGRAM_SYSTEM_PROMPT

        assert "no markdown fences" in DIAGRAM_SYSTEM_PROMPT.lower() or "triple backticks" in DIAGRAM_SYSTEM_PROMPT.lower()

    def test_diagram_prompt_defaults_to_flowchart(self):
        from document_generation import DIAGRAM_SYSTEM_PROMPT

        assert "default to **flowchart**" in DIAGRAM_SYSTEM_PROMPT


class TestMermaidValidation:
    """Test Mermaid syntax validation and helper functions."""

    def test_validate_valid_flowchart(self):
        from document_generation import _validate_mermaid_syntax

        assert _validate_mermaid_syntax("flowchart TD\n  A --> B") is None

    def test_validate_valid_erd(self):
        from document_generation import _validate_mermaid_syntax

        assert _validate_mermaid_syntax("erDiagram\n  USER ||--o{ ORDER : places") is None

    def test_validate_prose_returns_error(self):
        from document_generation import _validate_mermaid_syntax

        result = _validate_mermaid_syntax("Based on the provided input, it seems there is a misunderstanding.")
        assert result is not None
        assert "No valid Mermaid diagram type" in result

    def test_detect_flowchart_type(self):
        from document_generation import _detect_diagram_type

        assert _detect_diagram_type("flowchart TD\n  A --> B") == "user_flow"

    def test_detect_erd_type(self):
        from document_generation import _detect_diagram_type

        assert _detect_diagram_type("erDiagram\n  USER ||--o{ ORDER : places") == "erd"

    def test_strip_mermaid_fences(self):
        from document_generation import _strip_mermaid_fences

        assert _strip_mermaid_fences("```mermaid\nflowchart TD\n  A --> B\n```") == "flowchart TD\n  A --> B"

    def test_format_transcription(self):
        from document_generation import _format_transcription

        job = {
            "result": {
                "segments": [
                    {"speaker": "Speaker 1", "text": "Let's discuss the database schema."},
                    {"speaker": "Speaker 2", "text": "We need a users table."},
                ]
            }
        }
        result = _format_transcription(job)
        assert "[Speaker 1]: Let's discuss the database schema." in result
        assert "[Speaker 2]: We need a users table." in result

    def test_format_transcription_no_result(self):
        from document_generation import _format_transcription

        assert _format_transcription({}) == ""
        assert _format_transcription({"result": None}) == ""
        assert _format_transcription({"result": {}}) == ""


class TestGeneratePRD:
    """Test generate_prd function with mocked LLM."""

    @patch("document_generation.get_job")
    def test_generate_prd_with_document_context(self, mock_get_job):
        from document_generation import generate_prd

        mock_get_job.return_value = {
            "outcomes": [{"type": "decision", "title": "Use React", "detail": "Frontend", "confidence": 0.9}],
        }
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "# PRD\nGenerated content"}}],
        }

        doc_ctx = "## Reference Documents\n\n### spec.pdf\nProduct spec content"
        result = generate_prd("job-1", mock_app, document_context=doc_ctx)

        assert result == "# PRD\nGenerated content"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" in user_content
        assert "spec.pdf" in user_content

    @patch("document_generation.get_job")
    def test_generate_prd_without_document_context(self, mock_get_job):
        from document_generation import generate_prd

        mock_get_job.return_value = {
            "outcomes": [{"type": "decision", "title": "Use React", "detail": "Frontend", "confidence": 0.9}],
        }
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "# PRD\nGenerated content"}}],
        }

        result = generate_prd("job-1", mock_app)

        assert result == "# PRD\nGenerated content"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" not in user_content


class TestGenerateDiagram:
    """Test generate_diagram function with mocked LLM."""

    def _make_job_with_transcript(self):
        return {
            "result": {
                "segments": [
                    {"speaker": "Speaker 1", "text": "We need a payment processing flow."},
                    {"speaker": "Speaker 2", "text": "Users submit orders then we validate payment."},
                ]
            },
            "outcomes": [],
        }

    def _make_job_outcomes_only(self):
        return {
            "result": None,
            "outcomes": [
                {"type": "decision", "title": "Use React", "detail": "Frontend", "confidence": 0.9},
            ],
        }

    @patch("document_generation.get_job")
    def test_uses_transcript_when_available(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = self._make_job_with_transcript()
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "flowchart TD\n    A[Submit Order] --> B[Validate Payment]"}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert "flowchart TD" in mermaid
        assert dtype == "user_flow"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "[Speaker 1]" in user_content

    @patch("document_generation.get_job")
    def test_falls_back_to_outcomes(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = self._make_job_outcomes_only()
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "flowchart TD\n    A[Start] --> B[End]"}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert "flowchart TD" in mermaid

    @patch("document_generation.get_job")
    def test_detects_erd_type(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = self._make_job_with_transcript()
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "erDiagram\n    USER ||--o{ ORDER : places"}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert "erDiagram" in mermaid
        assert dtype == "erd"

    @patch("document_generation.get_job")
    def test_retries_on_invalid_output(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = self._make_job_with_transcript()
        mock_app = MagicMock()
        # First call returns prose, second returns valid diagram
        mock_app.llm.create_chat_completion.side_effect = [
            {"choices": [{"message": {"content": "Based on the input, here is a misunderstanding."}}]},
            {"choices": [{"message": {"content": "flowchart TD\n    A[Start] --> B[End]"}}]},
        ]

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert "flowchart TD" in mermaid
        assert mock_app.llm.create_chat_completion.call_count == 2

    @patch("document_generation.get_job")
    def test_retry_limit_respected(self, mock_get_job):
        from document_generation import generate_diagram, MAX_DIAGRAM_RETRIES

        mock_get_job.return_value = self._make_job_with_transcript()
        mock_app = MagicMock()
        # All calls return prose
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "This is not a diagram."}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        # 1 initial + MAX_DIAGRAM_RETRIES retries
        assert mock_app.llm.create_chat_completion.call_count == 1 + MAX_DIAGRAM_RETRIES

    @patch("document_generation.get_job")
    def test_includes_document_context(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = self._make_job_with_transcript()
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "flowchart TD\n    A[Payment] --> B[Stripe]"}}],
        }

        doc_ctx = "## Reference Documents\n\n### payments.docx\nStripe integration spec"
        mermaid, dtype = generate_diagram("job-1", mock_app, document_context=doc_ctx)

        assert "flowchart TD" in mermaid
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" in user_content

    @patch("document_generation.get_job")
    def test_strips_markdown_fences(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = self._make_job_with_transcript()
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "```mermaid\nflowchart TD\n    A --> B\n```"}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert mermaid.startswith("flowchart TD")
        assert "```" not in mermaid

    @patch("document_generation.get_job")
    def test_no_transcript_no_outcomes_raises(self, mock_get_job):
        from document_generation import generate_diagram

        mock_get_job.return_value = {"result": None, "outcomes": []}
        mock_app = MagicMock()

        with pytest.raises(ValueError, match="no transcription or outcomes"):
            generate_diagram("job-1", mock_app)

