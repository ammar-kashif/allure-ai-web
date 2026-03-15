"""LLM document generation: PRD prose and Mermaid diagrams from recording outcomes."""

from typing import Any

from storage import get_job

PRD_SYSTEM_PROMPT = """You are a technical writer. Generate a Professional Requirements Document (PRD) from the meeting outcomes below.

Structure the PRD with these sections:
1. **Overview** - Brief project summary based on the discussion
2. **Decisions Made** - Key decisions agreed upon
3. **Requirements** - Stated needs and constraints
4. **Action Items** - Tasks assigned with owners where known
5. **Risks & Blockers** - Impediments identified

Guidelines:
- Write in professional, clear prose
- Reference specific speakers and timestamps where relevant
- Group related items logically
- Use bullet points for lists
- Keep each section concise but complete
- Use markdown formatting (headers, bold, bullets)"""

USERFLOW_SYSTEM_PROMPT = """You are a diagram specialist. Generate a Mermaid flowchart diagram from the meeting outcomes below.

Rules for valid Mermaid syntax:
- Start with `flowchart TD` (top-down direction)
- Use simple alphanumeric node IDs (A, B, C or step1, step2)
- Use square brackets for labels: A[Start Process]
- Use --> for arrows with optional labels: A -->|action| B
- Use diamond braces for decisions: D{Decision?}
- Keep labels short (max 5 words)
- Do NOT use special characters in labels (no parentheses, quotes, or colons)
- Maximum 12 nodes to keep the diagram readable
- Output ONLY the Mermaid code, no explanation or markdown fences

Example:
flowchart TD
    A[User Records Meeting] --> B[Transcription]
    B --> C{Outcomes Extracted?}
    C -->|Yes| D[Review Outcomes]
    C -->|No| E[Retry]
    D --> F[Generate Documents]"""

ERD_SYSTEM_PROMPT = """You are a diagram specialist. Generate a Mermaid Entity Relationship Diagram from the meeting requirements and entities discussed.

Rules for valid Mermaid syntax:
- Start with `erDiagram`
- Use UPPERCASE entity names with no spaces: USER, PROJECT, RECORDING
- Relationships use: ||--o{ (one to many), ||--|| (one to one), }o--o{ (many to many)
- Attributes use: string, int, date types
- Keep to essential entities only (max 6)
- Output ONLY the Mermaid code, no explanation or markdown fences

Example:
erDiagram
    USER ||--o{ RECORDING : creates
    RECORDING ||--o{ OUTCOME : contains
    OUTCOME ||--o| TASK : promotes_to
    RECORDING {
        string id
        string title
        int duration
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


def generate_prd(job_id: str, app_state: object) -> str:
    """Generate a PRD document from a recording's outcomes via LLM.

    Fetches outcomes from storage, builds a prompt, calls the LLM,
    and returns the generated markdown string.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise ValueError(f"Job {job_id} has no outcomes")

    formatted = format_outcomes_for_generation(outcomes)

    messages = [
        {"role": "system", "content": PRD_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Generate a PRD from these meeting outcomes:\n\n{formatted}",
        },
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.3,
        max_tokens=4096,
    )

    return response["choices"][0]["message"]["content"]


def generate_diagram(job_id: str, diagram_type: str, app_state: object) -> str:
    """Generate a Mermaid diagram from a recording's outcomes via LLM.

    Args:
        job_id: The recording job ID.
        diagram_type: Either "user_flow" or "erd".
        app_state: FastAPI app state with .llm attribute.

    Returns:
        Raw Mermaid code string.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise ValueError(f"Job {job_id} has no outcomes")

    if diagram_type == "user_flow":
        system_prompt = USERFLOW_SYSTEM_PROMPT
    elif diagram_type == "erd":
        system_prompt = ERD_SYSTEM_PROMPT
    else:
        raise ValueError(f"Invalid diagram type: {diagram_type}")

    formatted = format_outcomes_for_generation(outcomes)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Generate a Mermaid diagram from these meeting outcomes:\n\n{formatted}",
        },
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )

    return response["choices"][0]["message"]["content"]
