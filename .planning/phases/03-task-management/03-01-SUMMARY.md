---
phase: 03-task-management
plan: 01
subsystem: api, database
tags: [sqlite, tanstack-query, zod, crud, rest-api]

requires:
  - phase: 01-recording-pipeline
    provides: SQLite DB layer and schema patterns
  - phase: 02-ai-extraction
    provides: Task type and promote-to-task flow
provides:
  - Full CRUD data layer for tasks (types, DB functions, API routes, hooks)
  - Extended Task type with priority, dueDate, assignee, tags
  - listTasks with status filter and text search
  - Reusable TanStack Query hooks for task operations
affects: [03-task-management]

tech-stack:
  added: [zod (validation in task routes)]
  patterns: [zod schema validation in API routes, dynamic SQL WHERE clause building]

key-files:
  created:
    - src/app/api/tasks/route.ts
    - src/app/api/tasks/[id]/route.ts
    - src/hooks/use-tasks.ts
  modified:
    - src/types/outcome.ts
    - src/lib/db/schema.sql
    - src/lib/db/tasks.ts

key-decisions:
  - "Used zod for request validation in task API routes (first route to use zod)"
  - "Made sourceOutcomeId/sourceRecordingId/backlink nullable for manually-created tasks"
  - "Priority sort via SQL CASE expression (high=1, medium=2, low=3)"

patterns-established:
  - "Zod validation: safeParse with 400 error response including issue details"
  - "Dynamic SQL filters: build WHERE clauses and params arrays conditionally"

requirements-completed: [TASK-01, TASK-02]

duration: 3min
completed: 2026-03-13
---

# Phase 03 Plan 01: Task Data Layer Summary

**Full CRUD task API with extended schema (priority, dueDate, assignee, tags), zod validation, filtering/search, and TanStack Query hooks**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T19:58:01Z
- **Completed:** 2026-03-13T20:01:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Extended Task type with priority, dueDate, assignee, tags, and nullable source fields for manual task creation
- Full CRUD database functions (createTask, listTasks, updateTask, deleteTask) with priority-based sorting and text search
- REST API routes at /api/tasks and /api/tasks/[id] with zod request validation
- Four TanStack Query hooks (useTasks, useCreateTask, useUpdateTask, useDeleteTask) with cache invalidation and toast notifications

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend types, schema, and DB functions** - `01da678` (feat)
2. **Task 2: API routes and TanStack Query hooks** - `5b1cc17` (feat)

## Files Created/Modified
- `src/types/outcome.ts` - Added TaskStatus, TaskPriority types; TaskFilters, CreateTaskInput, UpdateTaskInput interfaces; extended Task interface
- `src/lib/db/schema.sql` - Added priority, due_date, assignee, tags columns to tasks table
- `src/lib/db/tasks.ts` - Added listTasks, updateTask, deleteTask; extended createTask with optional new fields
- `src/app/api/tasks/route.ts` - GET (list+filter) and POST (create) endpoints with zod validation
- `src/app/api/tasks/[id]/route.ts` - GET, PATCH, DELETE endpoints with zod validation
- `src/hooks/use-tasks.ts` - useTasks, useCreateTask, useUpdateTask, useDeleteTask hooks

## Decisions Made
- Used zod for request validation in task API routes -- first route to use zod, establishes pattern for future routes
- Made sourceOutcomeId, sourceRecordingId, backlink nullable (string | null) to support manually-created tasks alongside promoted tasks
- Priority sorting via SQL CASE expression (high=1, medium=2, low=3) then created_at DESC
- Used `crypto.randomUUID()` in DB layer (not API layer) for id generation with optional override

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Note: users with an existing allure.db file may need to delete it for the new schema columns to take effect.

## Next Phase Readiness
- Data layer complete, ready for Plan 02 (Task List View) and Plan 03 (Kanban Board)
- All hooks exported and ready for frontend consumption
- API testable independently via curl

## Self-Check: PASSED

- All 6 files verified present on disk
- Commits 01da678 and 5b1cc17 verified in git log
- TypeScript type-check passes (only pre-existing test error in route.test.ts)

---
*Phase: 03-task-management*
*Completed: 2026-03-13*
