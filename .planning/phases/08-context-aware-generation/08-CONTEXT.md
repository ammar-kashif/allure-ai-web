# Phase 8: Context-Aware Generation - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

PRD and Mermaid generation incorporates attached document text as context and produces product-focused output. Diagrams model the product/system discussed in the meeting, not the meeting flow itself. Prompts are overhauled for quality. No new generation types, no UI changes to generate buttons, no new document types.

</domain>

<decisions>
## Implementation Decisions

### Document Context Injection
- Attached doc text appended AFTER outcomes in the prompt, in a "Reference Documents" section
- Generation works without documents (same as today) — documents are optional context enrichment
- Multiple documents concatenated into one section, separated by filename headers
- When combined text exceeds context budget, hard-truncate with '[truncated]' marker
- No extra LLM pass for summarization — simple truncation

### Product-Focused Diagrams
- Overhaul existing user_flow and ERD prompts — same two types, better prompts, no new diagram types
- Auto-selection between user_flow and ERD preserved (existing `select_diagram_type`)
- Within auto-selection, LLM also considers whether a product flow or architecture diagram is more appropriate
- Explicit anti-pattern instruction: "Do NOT diagram the meeting itself. Diagram the product/system that was discussed."
- Diagrams grounded in document content — use exact entity names, flow steps, and domain language from attached docs
- Replace meeting-focused examples with product-focused examples in prompts

### PRD Prompt Overhaul
- Product spec document tone — reads like a real PRD, not meeting minutes
- Explicit guard: "Do NOT reference speakers, timestamps, or meeting logistics. Write as a standalone product spec."
- Restructured sections: Overview, Goals & Objectives, Functional Requirements, Non-Functional Requirements, Constraints, Open Questions
- Document content synthesized naturally — no citations like "According to doc X..."
- Replace current "reference speakers and timestamps" instruction with product-focused guidance

### Context Window Budget
- Fixed reserve approach: ~500 tokens system prompt, ~2000 outcomes, ~1500 generation output, ~4000 for documents
- Character-based estimation (~4 chars/token heuristic) — no tokenizer dependency
- When truncation occurs, add a note in the generated output: "Note: Some reference document content was truncated."
- Multiple documents get equal token split — each doc allocated same budget, truncated individually
- Silent truncation (no toast/UI notification), but transparency in generated output

### Claude's Discretion
- Exact prompt wording and examples for PRD and diagram generation
- Temperature and max_tokens tuning for improved output quality
- How the "Reference Documents" section is formatted in the prompt template
- Mermaid syntax validation or retry logic for invalid diagrams
- Exact character-per-token ratio if 4 is too coarse
- Architecture diagram node/label design within Mermaid constraints

</decisions>

<specifics>
## Specific Ideas

- Anti-pattern instructions are critical — the current prompts actively encourage meeting-focused output (examples show "User Records Meeting", PRD says "reference speakers")
- Product-standard PRD sections (Overview, Goals, Functional/Non-Functional Requirements, Constraints, Open Questions) make the demo more impressive — looks like a real product spec
- Documents grounding diagrams in real domain language is the key differentiator — "Order", "Payment", "User" from the attached spec rather than generic "Step 1", "Step 2"
- The truncation note in generated output gives transparency without cluttering the UI

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `document_generation.py`: All generation logic — PRD prompts, diagram prompts, `format_outcomes_for_generation()`, `select_diagram_type()`, `generate_prd()`, `generate_diagram()`
- `storage.py`: Has `get_job()` for outcomes; Phase 7 added attachment CRUD with `extracted_text` field
- `main.py`: Backend endpoints `POST /recordings/{id}/generate-prd` and `POST /recordings/{id}/generate-diagram`
- Next.js API routes: `generate-prd/route.ts` and `generate-diagram/route.ts` proxy to backend

### Established Patterns
- LLM called via `app_state.llm.create_chat_completion()` with messages array (system + user)
- Outcomes formatted as numbered list via `format_outcomes_for_generation()`
- Diagram type auto-selected by separate LLM call (`select_diagram_type()`)
- Frontend stores generated documents in SQLite via `createDocument()`
- n_ctx already set to 8192 (bumped in Phase 7)

### Integration Points
- `document_generation.py`: Rewrite all prompt constants, modify `generate_prd()` and `generate_diagram()` to accept and inject document context
- `storage.py`: Use existing `get_attachments()` to fetch extracted text for a recording
- `main.py`: Generation endpoints need to fetch attachments and pass text to generation functions
- No frontend changes needed — same generate buttons, same API contract, same document display

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-context-aware-generation*
*Context gathered: 2026-03-19*

