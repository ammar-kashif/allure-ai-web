---
phase: 08-context-aware-generation
plan: 01
subsystem: api
tags: [llm, prompt-engineering, context-injection, truncation, mermaid, prd]

requires:
  - phase: 07-document-attachments
    provides: "Attachment CRUD with extracted_text field in storage.py"
provides:
  - "build_document_context() with per-doc token budget truncation"
  - "get_attachments_with_text() storage query"
  - "Product-focused PRD, user_flow, and ERD prompts with anti-pattern guards"
  - "generate_prd and generate_diagram accept optional document_context parameter"
affects: [08-02-endpoint-wiring]

tech-stack:
  added: []
  patterns: [token-budget-truncation, context-injection-via-user-message, outcomes-before-documents]

key-files:
  created: []
  modified:
    - backend/document_generation.py
    - backend/storage.py
    - backend/tests/test_document_generation.py

key-decisions:
  - "Token budget constants: 500 system + 2000 outcomes + 4000 documents + 1500 generation = 8000 tokens"
  - "MAX_DOCUMENT_CHARS = 16000 (4 chars/token heuristic)"
  - "Outcomes framed as 'Primary Input' before documents as supplementary reference"
  - "Empty/whitespace-only extracted_text filtered at both storage and build_document_context layers"

patterns-established:
  - "Context injection: document text appended to user message after outcomes, never in system prompt"
  - "Per-doc budget splitting: max_chars divided equally among N documents, each truncated independently"
  - "Anti-pattern guards: explicit 'Do NOT diagram the meeting' instructions in all diagram prompts"

requirements-completed: [GEN-01, GEN-02, GEN-03]

duration: 4min
completed: 2026-03-19
---

# Phase 8 Plan 1: Prompts and Context Injection Summary

**Product-focused PRD/diagram prompts with document context injection, per-doc token budget truncation, and 24 passing tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-19T14:21:20Z
- **Completed:** 2026-03-19T14:25:31Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Overhauled all 4 prompt constants (PRD, user_flow, ERD, diagram selector) from meeting-focused to product-focused
- Added build_document_context() with equal per-doc budget splitting and truncation markers
- Added get_attachments_with_text() storage query with empty text filtering
- Updated generate_prd and generate_diagram with backward-compatible document_context parameter
- 24 tests covering context injection, truncation, prompt content validation, and generation functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Storage query + context injection + tests (TDD)** - `905cd46` (test: RED), `2036b55` (feat: GREEN)
2. **Task 2: Overhaul all prompts and update generation functions** - `21ce6d1` (feat)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `backend/storage.py` - Added get_attachments_with_text() query filtering empty text
- `backend/document_generation.py` - TOKEN_BUDGET constants, build_document_context(), rewritten prompts, updated function signatures
- `backend/tests/test_document_generation.py` - 24 tests replacing Wave 0 skip stubs

## Decisions Made
- Token budget allocation: 500+2000+4000+1500 = 8000 tokens (under 8192 n_ctx)
- 4 chars/token heuristic for MAX_DOCUMENT_CHARS = 16000
- Belt-and-suspenders empty text filtering at both storage query and build_document_context
- Outcomes labeled "Primary Input" to prevent document context from swamping meeting content

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Prompt overhaul and context injection plumbing complete
- Plan 02 can wire endpoints in main.py to call build_document_context and pass results to generation functions
- All functions have backward-compatible signatures (document_context defaults to "")

## Self-Check: PASSED

All 3 files verified present. All 3 commits verified in git log.

---
*Phase: 08-context-aware-generation*
*Completed: 2026-03-19*

