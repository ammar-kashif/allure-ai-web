"""Text extraction from PDF, DOCX, and TXT files."""

from typing import Optional, Tuple

MAX_EXTRACTED_CHARS = 100_000


def extract_text(file_path: str, file_type: str) -> Tuple[str, Optional[str]]:
    """Extract text from a file based on its type.

    Returns:
        Tuple of (extracted_text, error_message).
        On success, error_message is None.
        On failure, extracted_text is "" and error_message describes the issue.
    """
    file_type = file_type.lower().strip()

    extractors = {
        "pdf": _extract_pdf,
        "docx": _extract_docx,
        "txt": _extract_txt,
    }

    if file_type not in extractors:
        return ("", f"Unsupported file type: {file_type}")

    try:
        text = extractors[file_type](file_path)
        text = text.strip()
        if len(text) > MAX_EXTRACTED_CHARS:
            text = text[:MAX_EXTRACTED_CHARS]
        return (text, None)
    except Exception as e:
        return ("", str(e))


def _extract_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("PDF extraction unavailable: install pdfplumber (pip install pdfplumber)")

    pages_text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
    return "\n\n".join(pages_text)


def _extract_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("DOCX extraction unavailable: install python-docx (pip install python-docx)")

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text]
    return "\n\n".join(paragraphs)


def _extract_txt(file_path: str) -> str:
    """Extract text from a plain text file with UTF-8 fallback."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

