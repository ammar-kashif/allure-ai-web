---
phase: 09-integration-hardening-tech-debt
plan: 02
subsystem: api, docs
tags: [next.js, api-routes, race-condition, retry, documentation]

# Dependency graph
requires:
  - phase: 07-document-attachments
    provides: Document upload route and backend forwarding
provides:
  - Retry-resilient document forwarding when backendId is delayed
  - Accurate ROADMAP.md and REQUIREMENTS.md checkbox state
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [retry-loop-with-backoff for eventual consistency]

key-files:
  created: []
  modified:
    - src/app/api/recordings/[id]/documents/route.ts
    - .planning/ROADMAP.md

key-decisions:
  - "Simple retry loop (5 attempts, 1s apart) over queue/job infrastructure for backendId resolution"
  - "Restructured POST handler to save-then-forward instead of interleaved save+forward"

patterns-established:
  - "Retry pattern: poll getRecording in loop for eventual backendId availability"

requirements-completed: [RUX-02, DOC-02]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 9 Plan 2: Document Forwarding Fix & Documentation Sync Summary

**BackendId retry logic in documents route (5 attempts, 1s apart) and ROADMAP.md Phase 5/6 checkbox sync**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T10:25:33Z
- **Completed:** 2026-03-20T10:28:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Documents route now retries up to 5 times (1s apart) to resolve backendId before forwarding, fixing race condition when uploading from post-recording dialog
- Restructured POST handler: all files saved to disk first, then backendId resolved, then forwarding attempted
- Synced all Phase 5 (4 plans) and Phase 6 (3 plans) checkboxes to [x] in ROADMAP.md, matching audit findings

## Task Commits

Each task was committed atomically:

1. **Task 1: Add backendId retry logic to documents route** - `8cc1999` (feat)
2. **Task 2: Synchronize REQUIREMENTS.md and ROADMAP.md checkboxes** - `bf853e5` (chore)

## Files Created/Modified
- `src/app/api/recordings/[id]/documents/route.ts` - Added retry loop for backendId, restructured to save-then-forward
- `.planning/ROADMAP.md` - Marked Phase 5 and Phase 6 plan checkboxes as complete

## Decisions Made
- Used simple retry loop (5 attempts, 1s apart, 5s max wait) instead of job queue or background worker -- sufficient for the race condition window
- Restructured handler to save all files first, then resolve backendId, then forward -- ensures graceful degradation even if retries fail

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 9 Plan 2 complete; combined with Plan 1 this closes all audit findings (INT-01, INT-02, FLOW-01)
- v1.1 milestone ready for final closure

---
*Phase: 09-integration-hardening-tech-debt*
*Completed: 2026-03-20*

