# Phase 8: Context-Aware Generation - Research

**Researched:** 2026-03-19
**Domain:** LLM prompt engineering, document context injection, Mermaid diagram generation
**Confidence:** HIGH

## Summary

Phase 8 is a backend-only prompt engineering and context injection phase. The core work involves: (1) adding a new storage query to fetch attachment extracted_text for a recording, (2) modifying `generate_prd()` and `generate_diagram()` to accept and inject document context into prompts, (3) overhauling all prompt constants to produce product-focused output instead of meeting-focused output, and (4) wiring the generation endpoints in `main.py` to fetch attachments and pass their text downstream.

The existing codebase is well-structured for this change. `document_generation.py` contains all prompt constants and generation functions in one file. `storage.py` already has `list_attachments()` (metadata only) and `get_attachment()` (includes `extracted_text`). The LLM context window is already bumped to 8192 tokens. No frontend changes are needed -- same API contracts, same buttons, same document display.

**Primary recommendation:** Structure as a single plan with two waves -- Wave 1 rewrites prompts and adds context injection plumbing, Wave 2 wires endpoints and adds tests. All changes are in `document_generation.py`, `storage.py` (one new query), and `main.py` (two endpoint modifications).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Attached doc text appended AFTER outcomes in the prompt, in a "Reference Documents" section
- Generation works without documents (same as today) -- documents are optional context enrichment
- Multiple documents concatenated into one section, separated by filename headers
- When combined text exceeds context budget, hard-truncate with '[truncated]' marker
- No extra LLM pass for summarization -- simple truncation
- Overhaul existing user_flow and ERD prompts -- same two types, better prompts, no new diagram types
- Auto-selection between user_flow and ERD preserved (existing `select_diagram_type`)
- Within auto-selection, LLM also considers whether a product flow or architecture diagram is more appropriate
- Explicit anti-pattern instruction: "Do NOT diagram the meeting itself. Diagram the product/system that was discussed."
- Diagrams grounded in document content -- use exact entity names, flow steps, and domain language from attached docs
- Replace meeting-focused examples with product-focused examples in prompts
- Product spec document tone -- reads like a real PRD, not meeting minutes
- Explicit guard: "Do NOT reference speakers, timestamps, or meeting logistics. Write as a standalone product spec."
- Restructured PRD sections: Overview, Goals & Objectives, Functional Requirements, Non-Functional Requirements, Constraints, Open Questions
- Document content synthesized naturally -- no citations like "According to doc X..."
- Fixed reserve approach: ~500 tokens system prompt, ~2000 outcomes, ~1500 generation output, ~4000 for documents
- Character-based estimation (~4 chars/token heuristic) -- no tokenizer dependency
- When truncation occurs, add a note in the generated output: "Note: Some reference document content was truncated."
- Multiple documents get equal token split -- each doc allocated same budget, truncated individually
- Silent truncation (no toast/UI notification), but transparency in generated output

### Claude's Discretion
- Exact prompt wording and examples for PRD and diagram generation
- Temperature and max_tokens tuning for improved output quality
- How the "Reference Documents" section is formatted in the prompt template
- Mermaid syntax validation or retry logic for invalid diagrams
- Exact character-per-token ratio if 4 is too coarse
- Architecture diagram node/label design within Mermaid constraints

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GEN-01 | Mermaid diagrams model the product discussed, not the meeting flow | Prompt overhaul with anti-pattern instructions, product-focused examples replacing meeting-focused examples in USERFLOW_SYSTEM_PROMPT and ERD_SYSTEM_PROMPT |
| GEN-02 | PRD and Mermaid generation uses attached document text as context | New `get_attachments_text()` storage query, context injection into prompts via "Reference Documents" section, token budget truncation logic |
| GEN-03 | Improved prompts produce higher-quality PRD and Mermaid output | Complete rewrite of PRD_SYSTEM_PROMPT (new sections structure), USERFLOW_SYSTEM_PROMPT, ERD_SYSTEM_PROMPT, DIAGRAM_TYPE_SELECTOR_PROMPT with product-focused guidance |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| llama-cpp-python | existing | LLM inference via `Llama.create_chat_completion()` | Already in use, Phi-4-mini model loaded |
| sqlite3 | stdlib | Storage for attachment extracted_text | Already in use via `storage.py` |
| FastAPI | existing | Backend endpoints | Already in use |

### Supporting
No new libraries needed. This phase is pure prompt engineering + plumbing with existing dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Character-based token estimation | tiktoken tokenizer | User explicitly decided against tokenizer dependency; ~4 chars/token is adequate for budget heuristic |
| Simple truncation | Summarization pass | User explicitly decided no extra LLM pass |

## Architecture Patterns

### Files Modified
```
backend/
├── document_generation.py   # ALL prompt constants rewritten, context injection added
├── storage.py               # New query: get extracted_text for all attachments of a recording
└── main.py                  # Two endpoints modified to fetch attachments and pass to generation
```

### Pattern 1: Context Injection into Prompts
**What:** Append document text after outcomes in the user message, wrapped in a "Reference Documents" section
**When to use:** In `generate_prd()` and `generate_diagram()` when documents are present

```python
def build_document_context(recording_id: str, max_chars: int = 16000) -> str:
    """Fetch attachment texts and format as context section with truncation."""
    attachments = get_attachments_with_text(recording_id)
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
    return header + "\n\n".join(sections)
```

### Pattern 2: Token Budget Calculation
**What:** Fixed reserves with character-based estimation
**When to use:** When building prompts to stay within 8192 token context window

```python
# Budget allocation (in tokens, estimated at ~4 chars/token):
TOKEN_BUDGET = {
    "system_prompt": 500,    # ~2000 chars
    "outcomes": 2000,        # ~8000 chars
    "documents": 4000,       # ~16000 chars
    "generation": 1500,      # reserved for output
}
# Total: 8000 tokens, under 8192 n_ctx
MAX_DOCUMENT_CHARS = TOKEN_BUDGET["documents"] * 4  # 16000
```

### Pattern 3: Backward-Compatible Function Signatures
**What:** Add optional `document_context` parameter to generation functions
**When to use:** To maintain backward compatibility -- functions work with or without documents

```python
def generate_prd(job_id: str, app_state: object, document_context: str = "") -> str:
    # ... existing logic ...
    user_content = f"Generate a PRD from these meeting outcomes:\n\n{formatted}"
    if document_context:
        user_content += f"\n\n{document_context}"
    # ...
```

### Anti-Patterns to Avoid
- **Meeting-focused examples in prompts:** The current USERFLOW_SYSTEM_PROMPT example shows "User Records Meeting -> Transcription" -- this actively trains the LLM to produce meeting-flow diagrams. Replace with product-domain examples.
- **Referencing speakers/timestamps in PRD:** Current PRD_SYSTEM_PROMPT says "Reference specific speakers and timestamps where relevant" -- this is the exact opposite of what we want. Remove entirely.
- **Putting documents in system prompt:** Documents go in the user message after outcomes. System prompt stays fixed (cacheable, consistent behavior).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Exact tokenizer integration | Character-based heuristic (~4 chars/token) | User decision: no tokenizer dependency, heuristic sufficient for budget |
| Document summarization | Custom summarization pipeline | Simple truncation with '[truncated]' marker | User decision: no extra LLM pass |
| Mermaid syntax validation | Custom parser | Post-generation check for `flowchart` or `erDiagram` prefix | Full Mermaid parsing is complex; simple prefix check catches most issues |

## Common Pitfalls

### Pitfall 1: Prompt Too Long for Context Window
**What goes wrong:** Combined system prompt + outcomes + documents + generation reserve exceeds 8192 tokens, causing truncated or garbled output
**Why it happens:** No enforcement of token budget
**How to avoid:** Calculate budget upfront with character heuristic. Truncate documents to fit. Leave 1500-token reserve for generation output.
**Warning signs:** Generated output ends mid-sentence, or LLM returns empty content

### Pitfall 2: Mermaid Syntax Errors from LLM
**What goes wrong:** LLM produces invalid Mermaid that fails to render (unmatched brackets, special characters in labels, wrong arrow syntax)
**Why it happens:** Small models (Phi-4-mini) are less reliable at structured output than large models
**How to avoid:** Keep examples tight and simple. Limit node count (max 12). Instruct no special characters. Consider basic post-processing (strip markdown fences if present, trim whitespace).
**Warning signs:** Frontend Mermaid renderer shows error instead of diagram

### Pitfall 3: Empty Extracted Text
**What goes wrong:** Attachments exist but have empty `extracted_text` (extraction failed), polluting the prompt with empty sections
**Why it happens:** PDF/DOCX extraction can fail silently, storing empty string
**How to avoid:** Filter out attachments where `extracted_text` is empty or whitespace-only before building context
**Warning signs:** "Reference Documents" section in prompt has headers but no content

### Pitfall 4: LLM Ignoring Anti-Pattern Instructions
**What goes wrong:** Despite "Do NOT diagram the meeting" instruction, LLM still produces meeting-flow diagrams
**Why it happens:** Examples in the prompt are stronger signals than negative instructions for small models
**How to avoid:** Replace examples entirely with product-focused ones. Positive examples > negative instructions. Show what TO do, not just what NOT to do.
**Warning signs:** Generated diagrams still contain nodes like "Record Meeting", "Transcribe", "Extract Outcomes"

### Pitfall 5: Document Context Swamping Outcomes
**What goes wrong:** 4000 tokens of document text overwhelms 2000 tokens of outcomes, causing LLM to generate based mostly on documents ignoring the meeting
**Why it happens:** Recency bias -- LLM pays more attention to text at the end of the prompt
**How to avoid:** Place outcomes BEFORE documents. Frame documents as "reference/supplementary" not primary input. Outcomes section should have clear header "## Meeting Outcomes (Primary Input)".
**Warning signs:** Generated PRD has no connection to what was discussed in the meeting

## Code Examples

### Storage: Fetch Extracted Text for All Attachments
```python
# New function needed in storage.py
def get_attachments_with_text(recording_id: str) -> list[dict[str, Any]]:
    """Return attachments WITH extracted_text for a recording (for generation context)."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, filename, extracted_text FROM attachments WHERE recording_id = ? ORDER BY created_at",
        (recording_id,),
    ).fetchall()
    conn.row_factory = None
    return [dict(row) for row in rows]
```

### Endpoint Wiring: Pass Document Context to Generation
```python
# Modified endpoint in main.py
@app.post("/recordings/{job_id}/generate-prd")
async def generate_prd_endpoint(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise HTTPException(status_code=400, detail="No outcomes to generate from")

    from document_generation import generate_prd, build_document_context

    doc_context = build_document_context(job_id)
    content = await asyncio.to_thread(generate_prd, job_id, app.state, doc_context)
    return {
        "content": content,
        "title": f"PRD - {job.get('original_filename', 'Recording')}",
    }
```

### Overhauled PRD Prompt (Skeleton)
```python
PRD_SYSTEM_PROMPT = """You are a senior product manager writing a Product Requirements Document (PRD).

Generate a comprehensive PRD from the meeting outcomes and any reference documents provided.

Structure the PRD with these sections:
1. **Overview** - Product/feature summary and purpose
2. **Goals & Objectives** - What success looks like
3. **Functional Requirements** - What the system must do
4. **Non-Functional Requirements** - Performance, security, scalability constraints
5. **Constraints** - Technical, business, or timeline limitations
6. **Open Questions** - Unresolved items needing follow-up

Guidelines:
- Write as a standalone product specification document
- Do NOT reference speakers, timestamps, or meeting logistics
- Use domain-specific terminology from the outcomes and reference documents
- Synthesize information naturally -- do not cite sources
- Use markdown formatting (headers, bold, bullets, tables where appropriate)
- Be specific and actionable in requirements"""
```

### Overhauled User Flow Prompt (Skeleton)
```python
USERFLOW_SYSTEM_PROMPT = """You are a product architect. Generate a Mermaid flowchart that models the product or system discussed in the meeting outcomes.

Rules for valid Mermaid syntax:
- Start with `flowchart TD`
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
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Meeting-focused PRD prompts | Product-focused PRD prompts | This phase | PRD reads as real product spec |
| Meeting-flow diagram examples | Product/system diagram examples | This phase | Diagrams model the product discussed |
| No document context | Document context injection | This phase | Generation grounded in attached specs |
| No token budgeting | Character-based budget with truncation | This phase | Prevents context overflow |

## Open Questions

1. **Optimal temperature for product-focused output**
   - What we know: Current PRD uses 0.3, diagrams use 0.2
   - What's unclear: Whether these remain optimal with document context added
   - Recommendation: Keep current values initially; adjust if output quality degrades. Lower temperature (0.1-0.2) for diagrams to reduce syntax errors.

2. **Mermaid retry on syntax error**
   - What we know: Small models produce invalid Mermaid sometimes
   - What's unclear: Frequency of failures with improved prompts
   - Recommendation: Add basic post-processing (strip markdown fences, trim). Defer retry logic unless failure rate is high. This is Claude's discretion per CONTEXT.md.

3. **Character-per-token ratio accuracy**
   - What we know: ~4 chars/token is standard English heuristic
   - What's unclear: How well this holds for technical document text with code, tables, etc.
   - Recommendation: Use 4 as default. Could use 3.5 for safety margin. This is Claude's discretion per CONTEXT.md.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | backend/tests/ directory structure, pytest discovery |
| Quick run command | `cd backend && python -m pytest tests/test_document_generation.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEN-01 | Diagram prompts produce product-focused output, not meeting flow | unit | `cd backend && python -m pytest tests/test_document_generation.py -x -q -k "diagram"` | Stubs only |
| GEN-02 | Generation functions accept and inject document context | unit | `cd backend && python -m pytest tests/test_document_generation.py -x -q -k "context"` | No |
| GEN-03 | Improved prompts structure (correct sections, no speaker refs) | unit | `cd backend && python -m pytest tests/test_document_generation.py -x -q -k "prd"` | Stubs only |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_document_generation.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_document_generation.py` -- replace skip stubs with real tests for prompt content, context injection, truncation logic
- [ ] New test for `build_document_context()` function -- truncation, empty docs filtering, multi-doc budget splitting
- [ ] New test for `get_attachments_with_text()` storage query
- [ ] Tests should mock LLM calls (no actual model needed) -- verify prompt construction, not LLM output

## Sources

### Primary (HIGH confidence)
- `backend/document_generation.py` -- current prompt constants and generation functions (direct code review)
- `backend/storage.py` -- attachment schema with `extracted_text` field (direct code review)
- `backend/main.py` -- generation endpoints and LLM configuration, n_ctx=8192 (direct code review)
- `08-CONTEXT.md` -- locked user decisions on context injection, truncation, prompt structure

### Secondary (MEDIUM confidence)
- Mermaid syntax rules from existing working prompts (validated by current diagram generation)
- Token estimation heuristic (~4 chars/token) is standard for English text with mixed models

### Tertiary (LOW confidence)
- Optimal temperature values for Phi-4-mini with document context -- needs empirical tuning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing libraries
- Architecture: HIGH - straightforward plumbing, single file holds all prompts
- Pitfalls: HIGH - based on direct code review of current anti-patterns in prompts

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- no external dependency changes expected)
