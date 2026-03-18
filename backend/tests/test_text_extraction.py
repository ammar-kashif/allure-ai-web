"""Unit tests for text extraction module."""

import os
import tempfile

import pytest

from text_extraction import extract_text, MAX_EXTRACTED_CHARS


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_pdf(tmp_path):
    """Generate a minimal PDF with known text using pdfplumber-compatible format."""
    from docx import Document as _unused  # noqa: F401 — ensure python-docx installed

    # Use reportlab-free approach: generate raw PDF bytes
    text_content = "Hello from sample PDF."
    # Minimal valid PDF with text
    pdf_bytes = (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    )
    # Build the content stream
    stream_content = f"BT /F1 12 Tf 100 700 Td ({text_content}) Tj ET".encode()
    stream_obj = (
        f"4 0 obj<</Length {len(stream_content)}>>stream\n".encode()
        + stream_content
        + b"\nendstream endobj\n"
    )
    xref_offset = len(pdf_bytes) + len(stream_obj)
    full_pdf = (
        pdf_bytes
        + stream_obj
        + f"xref\n0 6\n0000000000 65535 f \n".encode()
    )
    # Simplified xref — enough for pdfplumber to parse
    entries = []
    # Build proper xref
    raw = pdf_bytes + stream_obj
    full_content = (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        + stream_obj
    )
    # Write to tmp and let pdfplumber try it
    path = str(tmp_path / "sample.pdf")
    with open(path, "wb") as f:
        f.write(full_content)
        # Add a trailer
        f.write(b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF\n")
    return path


@pytest.fixture
def sample_docx(tmp_path):
    """Generate a minimal DOCX with known text."""
    from docx import Document

    path = str(tmp_path / "sample.docx")
    doc = Document()
    doc.add_paragraph("Hello from sample DOCX.")
    doc.save(path)
    return path


@pytest.fixture
def sample_txt():
    """Return path to the sample text fixture."""
    return os.path.join(FIXTURES_DIR, "sample.txt")


class TestExtractPDF:
    def test_extract_pdf_returns_text(self, sample_pdf):
        text, error = extract_text(sample_pdf, "pdf")
        assert error is None or error == ""
        assert "Hello from sample PDF" in text

    def test_extract_pdf_nonexistent(self):
        text, error = extract_text("/nonexistent/file.pdf", "pdf")
        assert text == ""
        assert error is not None and error != ""


class TestExtractDOCX:
    def test_extract_docx_returns_text(self, sample_docx):
        text, error = extract_text(sample_docx, "docx")
        assert error is None or error == ""
        assert "Hello from sample DOCX." in text

    def test_extract_docx_nonexistent(self):
        text, error = extract_text("/nonexistent/file.docx", "docx")
        assert text == ""
        assert error is not None and error != ""


class TestExtractTXT:
    def test_extract_txt_returns_content(self, sample_txt):
        text, error = extract_text(sample_txt, "txt")
        assert error is None or error == ""
        assert "Hello from sample text file." in text

    def test_extract_txt_nonexistent(self):
        text, error = extract_text("/nonexistent/file.txt", "txt")
        assert text == ""
        assert error is not None and error != ""


class TestExtractEdgeCases:
    def test_unsupported_type(self, sample_txt):
        text, error = extract_text(sample_txt, "unsupported")
        assert text == ""
        assert "Unsupported file type: unsupported" in error

    def test_truncation(self, tmp_path):
        """Text longer than MAX_EXTRACTED_CHARS is truncated."""
        long_text = "A" * (MAX_EXTRACTED_CHARS + 1000)
        path = str(tmp_path / "long.txt")
        with open(path, "w") as f:
            f.write(long_text)
        text, error = extract_text(path, "txt")
        assert len(text) == MAX_EXTRACTED_CHARS
        assert error is None or error == ""
