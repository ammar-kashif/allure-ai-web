"""LLM document generation: PRD prose and Mermaid diagrams from recording outcomes."""

import re
from typing import Any

from storage import get_attachments_with_text, get_job

# Token budget allocation (in tokens, estimated at ~4 chars/token)
TOKEN_BUDGET = {
    "system_prompt": 500,   # ~2000 chars
    "outcomes": 2000,       # ~8000 chars
    "documents": 4000,      # ~16000 chars
    "generation": 1500,     # reserved for output
}
MAX_DOCUMENT_CHARS = TOKEN_BUDGET["documents"] * 4  # 16000


def build_document_context(recording_id: str, max_chars: int = MAX_DOCUMENT_CHARS) -> str:
    """Fetch attachment texts and format as a reference documents section with truncation.

    Args:
        recording_id: The recording to fetch attachments for.
        max_chars: Maximum total characters for all document text combined.

    Returns:
        Formatted reference documents section, or empty string if no attachments.
    """
    attachments = get_attachments_with_text(recording_id)
    # Filter out empty/whitespace-only extracted_text (belt-and-suspenders with storage filter)
    attachments = [a for a in attachments if a.get("extracted_text", "").strip()]
    if not attachments:
        return ""

    per_doc_budget = max_chars // len(attachments)
    sections = []
    truncated = False
    for att in attachments:
        text = att["extracted_text"]
        if len(text) > per_doc_budget:
            text = text[:per_doc_budget] + "\n[truncated]"
            truncated = True
        sections.append(f"### {att['filename']}\n{text}")

    header = "## Reference Documents\n"
    if truncated:
        header += "(Note: Some reference document content was truncated.)\n"
    header += "\n"
    return header + "\n\n".join(sections)


PRD_SYSTEM_PROMPT = """You are a senior product manager writing a Product Requirements Document (PRD).

Generate a comprehensive PRD from the meeting outcomes and any reference documents provided.

Structure the PRD with these sections:
1. **Overview** - Product or feature summary and purpose
2. **Goals & Objectives** - What success looks like, key metrics
3. **Functional Requirements** - What the system must do, organized by feature area
4. **Non-Functional Requirements** - Performance, security, scalability, and reliability constraints
5. **Constraints** - Technical, business, or timeline limitations
6. **Open Questions** - Unresolved items needing follow-up

Guidelines:
- Write as a standalone product specification document
- Do NOT reference speakers, timestamps, or meeting logistics
- Use domain-specific terminology from the outcomes and reference documents
- Synthesize information naturally -- do not cite sources
- Use markdown formatting (headers, bold, bullets, tables where appropriate)
- Be specific and actionable in requirements
- Group related requirements logically under each section"""

DIAGRAM_SYSTEM_PROMPT = """You are an expert at interpreting meeting transcriptions and generating Mermaid diagram code.

I will provide you with a meeting transcription. Analyze the content and produce **only valid Mermaid.js code** (latest standard) — no explanations, no commentary, no markdown fences, just raw Mermaid syntax.

## Diagram Type Selection

Use a combination of keyword detection and topic inference to determine the diagram type:

- **ERD** — if the transcription is about entities, data models, relationships, tables, databases, or structured records
- **Flowchart** — if the transcription is about processes, workflows, decisions, steps, or system interactions
- If signals point clearly to one type, use it regardless of how the conversation unfolded
- If no clear signal exists, default to **flowchart**

Base the diagram on what the meeting is *about*, not the sequence of how the conversation unfolded.

## Output Rules

- Output Mermaid code only — nothing else
- The code must be valid and renderable in standard Mermaid.js (latest)
- Use clear, meaningful labels derived directly from the transcription content
- Do not include triple backticks, language identifiers, or any surrounding text"""

DIAGRAM_FIX_PROMPT = """The Mermaid diagram you generated has a syntax error.

Error: {error}

Your previous output:
{code}

Fix the syntax error and output ONLY the corrected Mermaid code — no explanations, no markdown fences."""


def format_outcomes_for_generation(outcomes: list[dict[str, Any]]) -> str:
    """Format outcomes as a numbered list for LLM prompt input."""
    lines = []
    for i, o in enumerate(outcomes, 1):
        otype = o.get("type", "unknown")
        title = o.get("title", "Untitled")
        detail = o.get("detail", "")
        confidence = o.get("confidence", 0.0)
        lines.append(
            f"{i}. [{otype.upper()}] {title}\n"
            f"   Detail: {detail}\n"
            f"   Confidence: {confidence:.2f}"
        )
    return "\n\n".join(lines)


def generate_prd(job_id: str, app_state: object, document_context: str = "") -> str:
    """Generate a PRD document from a recording's outcomes via LLM.

    Fetches outcomes from storage, builds a prompt, calls the LLM,
    and returns the generated markdown string.

    Args:
        job_id: The recording job ID.
        app_state: FastAPI app state with .llm attribute.
        document_context: Optional formatted reference documents section.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise ValueError(f"Job {job_id} has no outcomes")

    formatted = format_outcomes_for_generation(outcomes)

    user_content = f"## Meeting Outcomes (Primary Input)\n\n{formatted}"
    if document_context:
        user_content += f"\n\n{document_context}"

    messages = [
        {"role": "system", "content": PRD_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.3,
        max_tokens=4096,
    )

    return response["choices"][0]["message"]["content"]


MERMAID_KEYWORDS_RE = re.compile(
    r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|gitGraph|mindmap|timeline|sankey|xychart|block)",
    re.MULTILINE,
)

MAX_DIAGRAM_RETRIES = 2


def _strip_mermaid_fences(raw: str) -> str:
    """Remove markdown code fences the LLM may add despite instructions."""
    raw = re.sub(r"^```\w*\n?", "", raw.strip())
    raw = re.sub(r"\n?```\s*$", "", raw)
    return raw.strip()


def _detect_diagram_type(code: str) -> str:
    """Detect diagram type from generated Mermaid code."""
    if code.lstrip().startswith("erDiagram"):
        return "erd"
    return "user_flow"


def _validate_mermaid_syntax(code: str) -> str | None:
    """Basic syntax validation. Returns error message or None if OK."""
    if not MERMAID_KEYWORDS_RE.search(code):
        return "No valid Mermaid diagram type detected in output"
    return None


def _format_transcription(job: dict[str, Any]) -> str:
    """Format job transcript segments into readable transcription text."""
    result = job.get("result")
    if not result or not result.get("segments"):
        return ""
    lines = []
    for seg in result["segments"]:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{speaker}]: {text}")
    return "\n".join(lines)


def generate_diagram(job_id: str, app_state: object, document_context: str = "") -> tuple[str, str]:
    """Generate a Mermaid diagram from a recording's transcription via LLM.

    Uses the full transcription as input. The LLM auto-selects diagram type
    (flowchart or ERD) based on content. Retries up to MAX_DIAGRAM_RETRIES
    times if the output has syntax errors, feeding the error back to the LLM.

    Args:
        job_id: The recording job ID.
        app_state: FastAPI app state with .llm attribute.
        document_context: Optional formatted reference documents section.

    Returns:
        Tuple of (mermaid_code, diagram_type).
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    transcription = _format_transcription(job)
    if not transcription:
        # Fall back to outcomes if no transcript segments
        outcomes = job.get("outcomes", [])
        if not outcomes:
            raise ValueError(f"Job {job_id} has no transcription or outcomes")
        transcription = format_outcomes_for_generation(outcomes)

    user_content = f'"""\n{transcription}\n"""'
    if document_context:
        user_content += f"\n\n{document_context}"

    messages = [
        {"role": "system", "content": DIAGRAM_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # Initial generation
    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )

    code = _strip_mermaid_fences(response["choices"][0]["message"]["content"])

    # Retry loop: feed syntax errors back to LLM
    for _ in range(MAX_DIAGRAM_RETRIES):
        error = _validate_mermaid_syntax(code)
        if error is None:
            break

        fix_messages = [
            {"role": "system", "content": DIAGRAM_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": code},
            {"role": "user", "content": DIAGRAM_FIX_PROMPT.format(error=error, code=code)},
        ]

        response = app_state.llm.create_chat_completion(
            messages=fix_messages,
            temperature=0.1,
            max_tokens=2048,
        )

        code = _strip_mermaid_fences(response["choices"][0]["message"]["content"])

    diagram_type = _detect_diagram_type(code)
    return code, diagram_type

