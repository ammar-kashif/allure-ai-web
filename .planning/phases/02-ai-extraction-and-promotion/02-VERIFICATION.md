---
phase: 02-ai-extraction-and-promotion
verified: 2026-03-15T17:10:00Z
status: human_needed
score: 21/21 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 18/21
  gaps_closed:
    - "All 6 extraction unit tests now pass — sample_job fixture replaced storage.jobs dict with storage.create_job() + storage.update_job() (commit 60a057b)"
    - "Unused variable lint warning in outcomes-tab.tsx resolved — map((outcome, i) changed to map((outcome) (commit 66ea7f8)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Evidence cross-navigation"
    expected: "Clicking an evidence link in the Outcomes tab switches to the Transcript tab, scrolls the highlighted utterance into view, and applies a yellow background that fades after ~3 seconds"
    why_human: "Scroll behavior, CSS transitions, and timing cannot be verified programmatically in the test environment"
  - test: "Promote toast and button replacement"
    expected: "After clicking Promote on an action item the toast says 'Task created' and the button is replaced with a Promoted checkmark. Same flow for requirement ('Requirement created')."
    why_human: "Toast rendering and in-flight UI mutation state require a running browser"
---

# Phase 02: AI Extraction and Promotion Verification Report

**Phase Goal:** Users can trigger AI extraction on a transcript and get structured outcomes (decisions, action items, requirements, blockers) with confidence scores and evidence links, then promote them into tasks and requirement records
**Verified:** 2026-03-15T17:10:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 02-04)

---

## Re-Verification Summary

**Previous status:** gaps_found (18/21)
**Current status:** human_needed (21/21 automated checks pass)

**Gaps closed:**

1. **Extraction test fixtures** — `sample_job` in `backend/tests/test_extraction.py` now uses `storage.create_job()` + `storage.update_job()` instead of the removed `storage.jobs` dict. All 6 extraction tests pass (commit 60a057b, verified by running `pytest tests/test_extraction.py -v`).
2. **Lint warning** — Unused `i` parameter removed from `typeOutcomes.map((outcome) => (` in `outcomes-tab.tsx` (commit 66ea7f8, verified by grep).

**No regressions:** Full backend suite: 34 passed, 6 skipped. Full frontend outcome suite: 14/14 passed.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | After STT completes, extraction is automatically enqueued without user action | VERIFIED | `job_queue.py`: after STT `update_job(extraction_status="pending")` then `await job_queue.put((job_id, "extract"))` |
| 2 | Extraction produces structured outcomes from transcript text — verified by tests | VERIFIED | All 6 extraction unit tests pass; `run_extraction` reads job via `get_job`, calls LLM, returns typed outcome dicts |
| 3 | Each outcome includes title, detail, confidence score (0-1), and evidence references | VERIFIED | `backend/models.py` Outcome model with `Field(ge=0, le=1)`; `extraction.py` builds outcome dict with all fields |
| 4 | Evidence references point to valid segment indices in the source transcript | VERIFIED | `extraction.py` lines 146-150: filters refs where `0 <= ref.segment_index < num_segments`; confirmed by test_invalid_segment_indices_filtered |
| 5 | GET /recordings/{id}/outcomes returns outcomes with extraction_status | VERIFIED | `main.py`: endpoint returns `OutcomesResponse(job_id, extraction_status, outcomes)` |
| 6 | Promoted tasks/requirements include backlink text: 'From: {recording} @ {timestamp} -- {speaker}' | VERIFIED | `extraction.py` `format_backlink()` produces exact format; test_backlink_format confirms; used in promote endpoint |
| 7 | POST /recordings/{id}/extract enforces one-shot extraction — returns 409 if extraction_status is not 'none' or 'failed' | VERIFIED | `main.py`: guard allows 'none' or 'failed'; 4 API tests for this guard all pass |
| 8 | Frontend TypeScript types exist for Outcome, EvidenceRef, Task, RequirementRecord, OutcomesResponse | VERIFIED | `src/types/outcome.ts` exports all required types |
| 9 | SQLite schema includes outcomes, tasks, and requirement_records tables | VERIFIED | `src/lib/db/schema.sql` contains CREATE TABLE IF NOT EXISTS for all three tables |
| 10 | Proxy routes forward outcome/extract/promote requests to Python backend | VERIFIED | All three routes fetch from `localhost:8000` with error handling |
| 11 | useOutcomes hook fetches and caches outcomes for a recording | VERIFIED | `src/hooks/use-outcomes.ts`: queries `/api/recordings/${recordingId}/outcomes` with staleTime: 30_000 |
| 12 | usePromoteOutcome hook promotes an outcome and updates local cache | VERIFIED | `src/hooks/use-outcomes.ts`: mutates `/api/outcomes/${outcomeId}/promote`, invalidates outcomes query on success |
| 13 | Evidence highlight store manages cross-tab highlight state | VERIFIED | `src/stores/evidence-highlight.ts`: Zustand store with setHighlight (auto-clear via setTimeout after 3000ms) |
| 14 | Recording detail page has three tabs: Info, Transcript, Outcomes | VERIFIED | `page.tsx`: TabsTrigger for info, transcript, outcomes; controlled by useEvidenceHighlight activeTab |
| 15 | Outcomes tab shows summary banner with total count, type breakdown, and review count | VERIFIED | `summary-banner.tsx` renders total, per-type badges, "Needs review: N" amber badge |
| 16 | Outcomes are grouped in collapsible sections by type with count in header | VERIFIED | `outcomes-tab.tsx` maps sectionOrder; `outcome-section.tsx` has ChevronDown toggle |
| 17 | Each outcome card shows type icon, bold title, detail excerpt, confidence score with color, evidence link, and promote button | VERIFIED | `outcome-card.tsx` implements all; confidence badge green (>=0.80) or amber (<0.80) |
| 18 | Items below 0.80 confidence have amber left border, amber badge, and 'Needs review' label | VERIFIED | `outcome-card.tsx`: `border-l-amber-500` when `!isHighConfidence`; amber badge + "Needs review" span |
| 19 | Clicking evidence link switches to Transcript tab and highlights the utterance yellow for ~3 seconds | HUMAN NEEDED | Code path verified: `setHighlight(ref.segmentIndex)` -> store auto-clears after 3000ms -> `transcript-view.tsx` scrolls and applies `bg-yellow-200/60`; needs browser verification |
| 20 | Clicking Promote on action item creates a task with backlink, shows toast, replaces button with 'Promoted' | HUMAN NEEDED | Code path verified: `promote.mutate()` calls backend, `toast.success("Task created")` on success, promoted state shows Check icon + "Promoted" text; needs browser verification |
| 21 | Decisions and Blockers have no Promote button | VERIFIED | `outcome-card.tsx`: `canPromote = type === 'action_item' \|\| type === 'requirement'`; 2 component tests confirm |

**Score: 21/21 truths verified (19 automated, 2 human-needed)**

---

## Test Suite Status

**Backend (34 passed, 6 skipped — verified by run):**
- `tests/test_api.py`: 22/22 passed
- `tests/test_extraction.py`: 6/6 passed (previously 3/6 — gap closed)
- `tests/test_transcription.py`: 6/6 passed
- `tests/test_document_generation.py`: 6 skipped (LLM tests, pre-existing skips)

**Frontend outcome components (14/14 passed — verified by run):**
- `src/components/outcome/__tests__/outcome-card.test.tsx`: 9/9 passed
- `src/components/outcome/__tests__/outcomes-tab.test.tsx`: 5/5 passed

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/extraction.py` | LLM extraction logic | VERIFIED | 165 lines; run_extraction, format_backlink, EXTRACTION_SCHEMA exported |
| `backend/models.py` | Pydantic outcome models | VERIFIED | EvidenceRef, Outcome, OutcomesResponse, PromoteRequest, PromoteResponse |
| `backend/job_queue.py` | Tuple queue with STT/extract chaining | VERIFIED | 67 lines; auto-chains extraction after STT |
| `backend/main.py` | GET /outcomes, POST /extract, POST /promote endpoints | VERIFIED | All three endpoints with correct status codes and validation |
| `backend/storage.py` | Job storage with extraction_status and outcomes | VERIFIED | SQLite schema includes extraction_status, extraction_error, outcomes columns |
| `backend/tests/test_extraction.py` | Extraction tests with mocked LLM | VERIFIED | 6/6 tests pass; fixture uses storage.create_job() + storage.update_job() |
| `src/types/outcome.ts` | TypeScript outcome types | VERIFIED | OutcomeType, ExtractionStatus, EvidenceRef, Outcome, OutcomesResponse, Task, RequirementRecord |
| `src/lib/db/schema.sql` | outcomes, tasks, requirement_records tables | VERIFIED | All three CREATE TABLE IF NOT EXISTS statements present |
| `src/hooks/use-outcomes.ts` | useOutcomes, useExtractionStatus, usePromoteOutcome | VERIFIED | All three hooks with polling and cache invalidation |
| `src/stores/evidence-highlight.ts` | Zustand evidence highlight store | VERIFIED | setHighlight with auto-clear, clearHighlight, setActiveTab |
| `src/app/api/recordings/[id]/outcomes/route.ts` | GET proxy | VERIFIED | Fetches backend, transforms snake_case to camelCase, upserts SQLite |
| `src/app/api/recordings/[id]/extract/route.ts` | POST proxy | VERIFIED | Proxies to backend, returns 202 |
| `src/app/api/outcomes/[outcomeId]/promote/route.ts` | POST proxy with SQLite updates | VERIFIED | Proxies to backend, calls createTask/createRequirementRecord |
| `src/components/outcome/outcomes-tab.tsx` | Tab container with states | VERIFIED | Loading skeleton, error, empty, populated states; no lint warnings |
| `src/components/outcome/outcome-card.tsx` | Outcome card with confidence and promote | VERIFIED | 173 lines; confidence coloring, evidence links, promote flow |
| `src/components/outcome/outcome-section.tsx` | Collapsible section per type | VERIFIED | 57 lines; ChevronDown toggle, type icon and count |
| `src/components/outcome/summary-banner.tsx` | Stats banner | VERIFIED | 76 lines; total, type breakdown, needs review count |
| `src/app/(dashboard)/recordings/[id]/page.tsx` | Tabbed detail page | VERIFIED | TabsTrigger for info/transcript/outcomes; controlled via useEvidenceHighlight store |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/job_queue.py` | `backend/extraction.py` | `run_extraction` call after STT | WIRED | `from extraction import run_extraction` inside elif branch, called via `asyncio.to_thread` |
| `backend/extraction.py` | `llama_cpp.Llama` | `create_chat_completion` with JSON schema | WIRED | `app_state.llm.create_chat_completion(messages, response_format, temperature, max_tokens)` |
| `backend/main.py` | `backend/storage.py` | `get/update job with outcomes` | WIRED | `get_job` and `update_job` with outcomes kwarg |
| `src/hooks/use-outcomes.ts` | `src/app/api/recordings/[id]/outcomes/route.ts` | `apiClient.get` | WIRED | `apiClient.get(/api/recordings/${recordingId}/outcomes)` |
| `src/app/api/recordings/[id]/outcomes/route.ts` | backend GET /recordings/{id}/outcomes | fetch to localhost:8000 | WIRED | `fetch(${BACKEND_URL}/recordings/${recording.backendId}/outcomes)` |
| `src/app/api/outcomes/[outcomeId]/promote/route.ts` | backend POST /recordings/{id}/outcomes/{index}/promote | fetch proxy | WIRED | `fetch(${BACKEND_URL}/recordings/.../outcomes/${outcomeIndex}/promote)` |
| `src/components/outcome/outcome-card.tsx` | `src/stores/evidence-highlight.ts` | `setHighlight` on evidence click | WIRED | Imports `useEvidenceHighlight`; calls `setHighlight(ref.segmentIndex)` |
| `src/components/outcome/outcome-card.tsx` | `src/hooks/use-outcomes.ts` | `usePromoteOutcome` on promote click | WIRED | Imports `usePromoteOutcome`; calls `promote.mutate(...)` |
| `src/components/transcript/transcript-view.tsx` | `src/stores/evidence-highlight.ts` | reads highlightUtteranceIndex, scrolls | WIRED | Reads `highlightUtteranceIndex`; useEffect scrolls to `data-utterance-index` element |
| `src/app/(dashboard)/recordings/[id]/page.tsx` | `src/stores/evidence-highlight.ts` | `activeTab` controls displayed tab | WIRED | Reads `activeTab` and `setActiveTab` from store; `<Tabs value={activeTab}>` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EXT-01 | 02-01 | AI extracts structured outcomes (decisions, action items, requirements, blockers) | SATISFIED | `extraction.py` run_extraction; 4 outcome types enforced in EXTRACTION_SCHEMA and Pydantic model; all 6 extraction tests pass |
| EXT-02 | 02-01 | Each outcome includes title, details, confidence score, and evidence link | SATISFIED | Outcome model has title, detail, confidence (0-1 validated), evidence_refs list |
| EXT-03 | 02-02, 02-03 | Outcomes display grouped by type with confidence indicators | SATISFIED | outcomes-tab.tsx groups by sectionOrder; confidence badge green/amber with numeric score |
| EXT-04 | 02-03 | Items below 0.80 confidence are visually flagged for review | SATISFIED | outcome-card.tsx: amber left border + amber badge + "Needs review" label for confidence < 0.8 |
| EXT-05 | 02-02, 02-03 | User can promote action items to tasks with backlinks to source evidence | SATISFIED | promote endpoint maps action_item -> task; format_backlink() builds backlink; usePromoteOutcome hook; promote button in outcome-card |
| EXT-06 | 02-02, 02-03 | User can promote requirements to requirement records with backlinks | SATISFIED | promote endpoint maps requirement -> requirement; createRequirementRecord called in promote route |
| EXT-07 | 02-01, 02-03 | Promoted tasks/requirements retain evidence links to original transcript and audio timestamp | SATISFIED | backlink format "From: {title} @ {mm:ss} -- {speaker}" stored in PromoteResponse; createTask/createRequirementRecord receives backlink |

All 7 EXT requirements are covered across the 3 plans. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | Both previously-flagged anti-patterns are resolved |

The `storage.jobs` dict anti-pattern in `test_extraction.py` is gone. The unused `i` variable in `outcomes-tab.tsx` is gone. The `(_, i)` in `OutcomesLoadingSkeleton` at line 111 is not a lint issue — `i` is used as the `key` prop in that context.

---

## Human Verification Required

### 1. Evidence Cross-Navigation

**Test:** Navigate to a ready recording with completed extraction. Open the Outcomes tab and click any evidence link (timestamp + speaker text with ExternalLink icon) on an outcome card.
**Expected:** The active tab switches to "Transcript", the targeted utterance scrolls into view smoothly, and a yellow background (`bg-yellow-200/60`) appears on the utterance and fades away over approximately 3 seconds.
**Why human:** Scroll behavior, CSS transition timing, and the visual fade effect cannot be asserted from vitest/happy-dom.

### 2. Promote Flow with Toast and State Change

**Test:** On a ready recording with outcomes, click the "Promote" button on an action item. Then repeat with a requirement.
**Expected:** Action item: toast reads "Task created", button becomes a green checkmark with "Promoted" text, and cannot be clicked again. Requirement: toast reads "Requirement created", same button replacement. Decisions and Blockers should have no Promote button.
**Why human:** Toast library (sonner) rendering, real mutation state, and in-flight loading spinner require a running browser with the live backend.

---

_Verified: 2026-03-15T17:10:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — after Plan 02-04 gap closure_
