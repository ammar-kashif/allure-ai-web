---
phase: 02-ai-extraction-and-promotion
plan: 02
subsystem: api, database, ui
tags: [tanstack-query, zustand, sqlite, next-api-routes, proxy]

requires:
  - phase: 01-recording-and-transcription-pipeline
    provides: Recording types, SQLite schema, db/recordings CRUD, proxy route pattern
provides:
  - TypeScript types for outcomes, evidence refs, tasks, requirement records
  - SQLite schema extensions (outcomes, tasks, requirement_records tables)
  - Proxy API routes for outcomes, extract, promote
  - TanStack Query hooks (useOutcomes, useExtractionStatus, usePromoteOutcome)
  - Zustand evidence highlight store with auto-clear
affects: [02-03-outcomes-ui, task-management]

tech-stack:
  added: []
  patterns: [backend-outcome-transform, sqlite-outcome-persistence, polling-with-auto-stop]

key-files:
  created:
    - src/types/outcome.ts
    - src/lib/db/outcomes.ts
    - src/lib/db/tasks.ts
    - src/app/api/recordings/[id]/outcomes/route.ts
    - src/app/api/recordings/[id]/extract/route.ts
    - src/app/api/outcomes/[outcomeId]/promote/route.ts
    - src/hooks/use-outcomes.ts
    - src/stores/evidence-highlight.ts
  modified:
    - src/lib/db/schema.sql

key-decisions:
  - "Backend snake_case to frontend camelCase transform in outcomes proxy route"
  - "Outcomes persisted to frontend SQLite on every fetch for offline resilience"
  - "Evidence highlight auto-clears after 3000ms via setTimeout with cleanup"

patterns-established:
  - "Outcome proxy pattern: fetch from backend, transform, persist to SQLite, return"
  - "Polling hook pattern: refetchInterval returns false to stop, invalidates related queries on completion"

requirements-completed: [EXT-03, EXT-05, EXT-06]

duration: 2min
completed: 2026-03-12
---

# Phase 2 Plan 2: Frontend Data Layer Summary

**Outcome types, SQLite persistence, proxy API routes, TanStack Query hooks with polling, and Zustand evidence highlight store**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T11:21:27Z
- **Completed:** 2026-03-12T11:23:45Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Complete TypeScript type system for outcomes, evidence refs, tasks, and requirement records
- SQLite schema with outcomes, tasks, and requirement_records tables following existing patterns
- Three proxy API routes (outcomes, extract, promote) with SQLite persistence on fetch
- TanStack Query hooks with polling for extraction status and cache invalidation on promotion
- Zustand evidence highlight store with auto-clear and tab switching

## Task Commits

Each task was committed atomically:

1. **Task 1: TypeScript types, SQLite schema, and database CRUD modules** - `5f6005b` (feat)
2. **Task 2: Proxy API routes, TanStack Query hooks, and Zustand evidence store** - `4a165e6` (feat)

## Files Created/Modified
- `src/types/outcome.ts` - TypeScript types: Outcome, OutcomeType, EvidenceRef, ExtractionStatus, OutcomesResponse, Task, RequirementRecord
- `src/lib/db/schema.sql` - Extended with outcomes, tasks, requirement_records tables
- `src/lib/db/outcomes.ts` - CRUD: getOutcomesByRecording, upsertOutcomes, updateOutcomePromotion
- `src/lib/db/tasks.ts` - CRUD: createTask, createRequirementRecord, getTask, getRequirementRecord
- `src/app/api/recordings/[id]/outcomes/route.ts` - GET proxy with SQLite persistence
- `src/app/api/recordings/[id]/extract/route.ts` - POST proxy for manual extraction trigger
- `src/app/api/outcomes/[outcomeId]/promote/route.ts` - POST proxy with SQLite updates
- `src/hooks/use-outcomes.ts` - useOutcomes, useExtractionStatus (polling), usePromoteOutcome hooks
- `src/stores/evidence-highlight.ts` - Zustand store for cross-tab evidence highlighting

## Decisions Made
- Backend snake_case fields transformed to frontend camelCase in the outcomes proxy route
- Outcomes persisted to frontend SQLite on every fetch for offline resilience
- Evidence highlight auto-clears after 3000ms via setTimeout with proper cleanup of previous timers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete data layer ready for UI plan (02-03) to build outcomes panel, evidence links, and promote buttons
- All hooks and stores exported and ready for component consumption
- Proxy routes handle error cases and backend unavailability gracefully

---
*Phase: 02-ai-extraction-and-promotion*
*Completed: 2026-03-12*
