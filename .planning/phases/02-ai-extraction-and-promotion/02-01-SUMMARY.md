---
phase: 02-ai-extraction-and-promotion
plan: 01
subsystem: api
tags: [llama-cpp, phi-4-mini, extraction, fastapi, pydantic, job-queue]

# Dependency graph
requires:
  - phase: 01.1-python-backend
    provides: FastAPI app, job queue, storage, Moonshine STT pipeline
provides:
  - LLM extraction module with JSON schema-constrained output
  - Outcome Pydantic models (EvidenceRef, Outcome, OutcomesResponse)
  - Chained job queue (STT -> extract auto-chaining)
  - GET /outcomes, POST /extract, POST /promote endpoints
  - Promotion flow with backlink generation
affects: [02-02-frontend-data-layer, 02-03-outcomes-ui]

# Tech tracking
tech-stack:
  added: [llama-cpp-python (runtime dep, mocked in tests)]
  patterns: [tuple-based job queue, JSON schema-constrained LLM, one-shot extraction guard]

key-files:
  created:
    - backend/extraction.py
    - backend/tests/test_extraction.py
  modified:
    - backend/models.py
    - backend/storage.py
    - backend/job_queue.py
    - backend/main.py
    - backend/tests/test_api.py
    - backend/tests/conftest.py

key-decisions:
  - "Tuple-based queue (job_id, job_type) for STT/extract dispatch in single worker"
  - "Import run_extraction inside elif branch to avoid circular imports"
  - "Promote endpoint uses outcome_index (positional) not outcome_id for simplicity"
  - "Backlink uses first evidence_ref timestamp and speaker"

patterns-established:
  - "Chained job queue: after STT completes, auto-enqueue extraction"
  - "One-shot guard: POST /extract returns 409 unless extraction_status is 'none'"
  - "Promotion mapping: action_item -> task, requirement -> requirement"

requirements-completed: [EXT-01, EXT-02, EXT-07]

# Metrics
duration: 4min
completed: 2026-03-12
---

# Phase 02 Plan 01: Backend Extraction Pipeline Summary

**LLM extraction module with Phi-4-mini JSON schema constraint, chained job queue, and promotion endpoints with backlink generation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-12T11:21:08Z
- **Completed:** 2026-03-12T11:25:30Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Extraction module with SYSTEM_PROMPT, EXTRACTION_SCHEMA, run_extraction, format_transcript_for_prompt, format_backlink
- Pydantic models: EvidenceRef, Outcome, OutcomesResponse, PromoteRequest, PromoteResponse with StatusResponse extended
- Job queue upgraded to tuple-based dispatch with auto-chaining STT -> extract
- Three new endpoints: GET /outcomes, POST /extract (one-shot guard), POST /promote (type-aware with backlink)
- 31 total backend tests passing (6 extraction + 13 new API + 12 existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extraction module, Pydantic models, and backend tests** - `3bdc06d` (feat)
2. **Task 2: Job queue chaining, endpoints, and API tests** - `c7fecfc` (feat)

## Files Created/Modified
- `backend/extraction.py` - LLM extraction logic with run_extraction, format functions, EXTRACTION_SCHEMA
- `backend/models.py` - Added EvidenceRef, Outcome, OutcomesResponse, PromoteRequest, PromoteResponse; extended StatusResponse
- `backend/storage.py` - Added extraction_status, extraction_error, outcomes fields to job dict
- `backend/job_queue.py` - Tuple-based queue with STT/extract dispatch and auto-chaining
- `backend/main.py` - Added GET /outcomes, POST /extract, POST /promote endpoints; updated upload to use tuple queue
- `backend/tests/test_extraction.py` - 6 tests for extraction module with mocked LLM
- `backend/tests/test_api.py` - 13 new tests for outcomes, promotion, and one-shot extraction guard
- `backend/tests/conftest.py` - Comment update for tuple queue drain

## Decisions Made
- Used tuple-based queue `(job_id, job_type)` instead of separate queues for STT and extraction to maintain sequential processing
- Import run_extraction inside elif branch to prevent circular import (extraction.py imports from storage.py)
- Promote endpoint uses positional outcome_index rather than outcome_id for URL simplicity
- Backlink generated from first evidence_ref's timestamp and speaker (fallback to 0:00/Unknown if no refs)

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

**External services require manual configuration.** The Phi-4-mini GGUF model must be downloaded before running extraction in production:
```bash
huggingface-cli download bartowski/microsoft_Phi-4-mini-instruct-GGUF --include 'microsoft_Phi-4-mini-instruct-Q4_K_M.gguf' --local-dir ./backend/models/
```

Tests do not require the model (all LLM calls are mocked).

## Issues Encountered
None

## Next Phase Readiness
- Backend extraction pipeline complete, ready for frontend data layer (02-02) and outcomes UI (02-03)
- All endpoints tested and working with mocked LLM
- Production deployment requires llama-cpp-python installation and model download

---
*Phase: 02-ai-extraction-and-promotion*
*Completed: 2026-03-12*

## Self-Check: PASSED
- All 8 files exist on disk
- Commits 3bdc06d and c7fecfc verified in git log
- 31/31 tests passing

