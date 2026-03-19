"""LLM document generation: PRD prose and Mermaid diagrams from recording outcomes."""

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

USERFLOW_SYSTEM_PROMPT = """You are a product architect. Generate a Mermaid flowchart that models the product or system discussed in the meeting outcomes.

Rules for valid Mermaid syntax:
- Start with `flowchart TD` (top-down direction)
- Use simple alphanumeric node IDs (A, B, C or step1, step2)
- Use square brackets for labels: A[User Submits Order]
- Use --> for arrows with optional labels: A -->|validates| B
- Use diamond braces for decisions: D{Payment Valid?}
- Keep labels short (max 5 words)
- Do NOT use special characters in labels (no parentheses, quotes, or colons)
- Maximum 12 nodes for readability
- Output ONLY the Mermaid code, no explanation or markdown fences

IMPORTANT: Diagram the PRODUCT or SYSTEM discussed, NOT the meeting itself.
Use entity names and terminology from the outcomes and reference documents.

Example:
flowchart TD
    A[Customer Places Order] --> B[Validate Payment]
    B --> C{Payment Valid?}
    C -->|Yes| D[Process Order]
    C -->|No| E[Show Error]
    D --> F[Send Confirmation]
    D --> G[Update Inventory]"""

ERD_SYSTEM_PROMPT = """You are a product architect. Generate a Mermaid Entity Relationship Diagram that models the data entities of the product or system discussed in the meeting outcomes.

Rules for valid Mermaid syntax:
- Start with `erDiagram`
- Use UPPERCASE entity names with no spaces: USER, ORDER, PRODUCT
- Relationships use: ||--o{ (one to many), ||--|| (one to one), }o--o{ (many to many)
- Attributes use: string, int, date types
- Keep to essential entities only (max 6)
- Output ONLY the Mermaid code, no explanation or markdown fences

IMPORTANT: Diagram the PRODUCT or SYSTEM discussed, NOT the meeting itself.
Use entity names from the outcomes and reference documents.

Example:
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER_ITEM }o--|| PRODUCT : references
    ORDER ||--|| PAYMENT : has
    ORDER {
        string id
        string status
        int total
        date created_at
    }"""


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


DIAGRAM_TYPE_SELECTOR_PROMPT = """You are a product architect deciding what type of diagram best represents the product or system discussed in the meeting outcomes.

Given the outcomes below, decide which diagram type would be most useful:
- "user_flow" -- a flowchart showing product user journeys, processes, decision points, or workflows
- "erd" -- an entity relationship diagram showing data entities, their attributes, and relationships

Consider whether a product flow or architecture diagram is more appropriate for the discussed system.

Choose "user_flow" if the outcomes focus on processes, steps, decisions, or user interactions.
Choose "erd" if the outcomes focus on data models, entities, relationships, or system structure.

Respond with ONLY "user_flow" or "erd", nothing else."""


def select_diagram_type(outcomes: list[dict[str, Any]], app_state: object) -> str:
    """Use LLM to auto-select the best diagram type based on outcomes content."""
    formatted = format_outcomes_for_generation(outcomes)

    messages = [
        {"role": "system", "content": DIAGRAM_TYPE_SELECTOR_PROMPT},
        {
            "role": "user",
            "content": f"Meeting outcomes:\n\n{formatted}",
        },
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.0,
        max_tokens=20,
    )

    selected = response["choices"][0]["message"]["content"].strip().lower()
    if selected not in ("user_flow", "erd"):
        selected = "user_flow"  # safe default
    return selected


def generate_diagram(job_id: str, app_state: object, document_context: str = "") -> tuple[str, str]:
    """Generate a Mermaid diagram from a recording's outcomes via LLM.

    Auto-selects the best diagram type (user_flow or erd) based on content.

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

    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise ValueError(f"Job {job_id} has no outcomes")

    diagram_type = select_diagram_type(outcomes, app_state)

    if diagram_type == "user_flow":
        system_prompt = USERFLOW_SYSTEM_PROMPT
    else:
        system_prompt = ERD_SYSTEM_PROMPT

    formatted = format_outcomes_for_generation(outcomes)

    user_content = f"## Meeting Outcomes (Primary Input)\n\n{formatted}"
    if document_context:
        user_content += f"\n\n{document_context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )

    return response["choices"][0]["message"]["content"], diagram_type
