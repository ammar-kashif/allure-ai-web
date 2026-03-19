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


class TestPromptContent:
    """Validate prompt constants contain required content and no anti-patterns."""

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

    def test_userflow_prompt_contains_product_anti_pattern(self):
        from document_generation import USERFLOW_SYSTEM_PROMPT

        assert "PRODUCT or SYSTEM" in USERFLOW_SYSTEM_PROMPT

    def test_userflow_example_no_meeting_flow(self):
        from document_generation import USERFLOW_SYSTEM_PROMPT

        assert "Records Meeting" not in USERFLOW_SYSTEM_PROMPT
        assert "Transcription" not in USERFLOW_SYSTEM_PROMPT

    def test_userflow_has_product_focused_example(self):
        from document_generation import USERFLOW_SYSTEM_PROMPT

        # Should have a product-domain example
        assert "Customer Places Order" in USERFLOW_SYSTEM_PROMPT or "Order" in USERFLOW_SYSTEM_PROMPT

    def test_erd_example_no_meeting_entities(self):
        from document_generation import ERD_SYSTEM_PROMPT

        assert "RECORDING" not in ERD_SYSTEM_PROMPT
        assert "OUTCOME" not in ERD_SYSTEM_PROMPT

    def test_erd_has_product_anti_pattern(self):
        from document_generation import ERD_SYSTEM_PROMPT

        assert "PRODUCT or SYSTEM" in ERD_SYSTEM_PROMPT

    def test_diagram_selector_considers_product_focus(self):
        from document_generation import DIAGRAM_TYPE_SELECTOR_PROMPT

        assert "product" in DIAGRAM_TYPE_SELECTOR_PROMPT.lower()


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
        # Verify document context was included in the user message
        call_args = mock_app.llm.create_chat_completion.call_args
        user_msg = call_args[1]["messages"][1]["content"] if "messages" in call_args[1] else call_args[0][0][1]["content"]
        # Try keyword or positional
        messages = call_args.kwargs.get("messages") or call_args.args[0] if call_args.args else None
        if messages is None:
            messages = call_args[1]["messages"]
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
        # Verify no reference documents in user message
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" not in user_content

    @patch("document_generation.get_job")
    def test_generate_prd_outcomes_before_documents(self, mock_get_job):
        from document_generation import generate_prd

        mock_get_job.return_value = {
            "outcomes": [{"type": "decision", "title": "Use React", "detail": "Frontend", "confidence": 0.9}],
        }
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "# PRD"}}],
        }

        doc_ctx = "## Reference Documents\n\n### spec.pdf\nContent"
        generate_prd("job-1", mock_app, document_context=doc_ctx)

        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        # Outcomes should appear before documents
        outcomes_pos = user_content.index("Meeting Outcomes")
        docs_pos = user_content.index("Reference Documents")
        assert outcomes_pos < docs_pos


class TestGenerateDiagram:
    """Test generate_diagram function with mocked LLM."""

    @patch("document_generation.select_diagram_type")
    @patch("document_generation.get_job")
    def test_generate_diagram_with_document_context(self, mock_get_job, mock_select):
        from document_generation import generate_diagram

        mock_get_job.return_value = {
            "outcomes": [{"type": "decision", "title": "Use React", "detail": "Frontend", "confidence": 0.9}],
        }
        mock_select.return_value = "user_flow"
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "flowchart TD\n    A[Start] --> B[End]"}}],
        }

        doc_ctx = "## Reference Documents\n\n### arch.pdf\nArchitecture doc"
        mermaid, dtype = generate_diagram("job-1", mock_app, document_context=doc_ctx)

        assert "flowchart TD" in mermaid
        assert dtype == "user_flow"
        # Verify document context was included
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" in user_content

    @patch("document_generation.select_diagram_type")
    @patch("document_generation.get_job")
    def test_generate_diagram_without_document_context(self, mock_get_job, mock_select):
        from document_generation import generate_diagram

        mock_get_job.return_value = {
            "outcomes": [{"type": "decision", "title": "Use React", "detail": "Frontend", "confidence": 0.9}],
        }
        mock_select.return_value = "erd"
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "erDiagram\n    USER ||--o{ ORDER : places"}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert "erDiagram" in mermaid
        assert dtype == "erd"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" not in user_content


class TestEndpointWiring:
    """Verify generation functions correctly handle document context for endpoint wiring."""

    @patch("document_generation.get_job")
    def test_generate_prd_with_doc_context_includes_in_user_message(self, mock_get_job):
        """PRD generation includes document context in the user message when present."""
        from document_generation import generate_prd

        mock_get_job.return_value = {
            "outcomes": [
                {"type": "decision", "title": "Use GraphQL", "detail": "API layer", "confidence": 0.9}
            ],
        }
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "# PRD\nWith context"}}],
        }

        doc_ctx = "## Reference Documents\n\n### api-spec.pdf\nGraphQL schema definitions"
        result = generate_prd("job-1", mock_app, document_context=doc_ctx)

        assert result == "# PRD\nWith context"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" in user_content
        assert "api-spec.pdf" in user_content
        # Outcomes appear before documents
        assert user_content.index("Meeting Outcomes") < user_content.index("Reference Documents")

    @patch("document_generation.select_diagram_type")
    @patch("document_generation.get_job")
    def test_generate_diagram_with_doc_context_includes_in_user_message(
        self, mock_get_job, mock_select
    ):
        """Diagram generation includes document context in the user message when present."""
        from document_generation import generate_diagram

        mock_get_job.return_value = {
            "outcomes": [
                {"type": "requirement", "title": "Payment flow", "detail": "Stripe integration", "confidence": 0.85}
            ],
        }
        mock_select.return_value = "user_flow"
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "flowchart TD\n    A[Payment] --> B[Stripe]"}}],
        }

        doc_ctx = "## Reference Documents\n\n### payments.docx\nStripe payment integration spec"
        mermaid, dtype = generate_diagram("job-1", mock_app, document_context=doc_ctx)

        assert "flowchart TD" in mermaid
        assert dtype == "user_flow"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Reference Documents" in user_content
        assert "payments.docx" in user_content
        # Outcomes appear before documents
        assert user_content.index("Meeting Outcomes") < user_content.index("Reference Documents")

    @patch("document_generation.get_job")
    def test_generate_prd_backward_compat_no_docs(self, mock_get_job):
        """PRD generation works without document context (backward compatibility)."""
        from document_generation import generate_prd

        mock_get_job.return_value = {
            "outcomes": [
                {"type": "task", "title": "Build API", "detail": "REST endpoints", "confidence": 0.88}
            ],
        }
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "# PRD\nNo docs"}}],
        }

        result = generate_prd("job-1", mock_app)

        assert result == "# PRD\nNo docs"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Meeting Outcomes" in user_content
        assert "Reference Documents" not in user_content

    @patch("document_generation.select_diagram_type")
    @patch("document_generation.get_job")
    def test_generate_diagram_backward_compat_no_docs(self, mock_get_job, mock_select):
        """Diagram generation works without document context (backward compatibility)."""
        from document_generation import generate_diagram

        mock_get_job.return_value = {
            "outcomes": [
                {"type": "task", "title": "Build API", "detail": "REST endpoints", "confidence": 0.88}
            ],
        }
        mock_select.return_value = "erd"
        mock_app = MagicMock()
        mock_app.llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "erDiagram\n    API ||--o{ ENDPOINT : exposes"}}],
        }

        mermaid, dtype = generate_diagram("job-1", mock_app)

        assert "erDiagram" in mermaid
        assert dtype == "erd"
        messages = mock_app.llm.create_chat_completion.call_args.kwargs.get("messages")
        if messages is None:
            messages = mock_app.llm.create_chat_completion.call_args[1]["messages"]
        user_content = messages[1]["content"]
        assert "Meeting Outcomes" in user_content
        assert "Reference Documents" not in user_content
