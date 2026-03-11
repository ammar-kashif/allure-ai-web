---
phase: 01-recording-and-transcription-pipeline
plan: 02
subsystem: api, database
tags: [better-sqlite3, tanstack-query, next-api-routes, fastapi-proxy, polling]

requires:
  - phase: 01-recording-and-transcription-pipeline
    plan: 01
    provides: Recording types, audio recorder hooks, Zustand recording store

provides:
  - SQLite database singleton with better-sqlite3 (WAL mode, FK enforcement)
  - Recording CRUD operations (getRecordings, getRecording, createRecording, updateRecording, getRecordingCounts)
  - Project CRUD operations (getProjects, createProject)
  - API client fetch wrapper with typed error handling
  - Next.js API routes proxying uploads to FastAPI backend
  - Status polling endpoint with backend status mapping
  - Transcript proxy endpoint
  - TanStack Query hooks for recordings (list, detail, status polling, upload, assign)
  - TanStack Query hooks for projects (list, create)

affects: [01-03-recording-hub-ui, 01-04-transcript-display, 01-05-integration]

tech-stack:
  added: [better-sqlite3]
  patterns: [api-route-proxy, sqlite-singleton, tanstack-query-polling, formdata-proxy]

key-files:
  created:
    - src/lib/db/index.ts
    - src/lib/db/schema.sql
    - src/lib/db/recordings.ts
    - src/lib/db/projects.ts
    - src/lib/api/client.ts
    - src/app/api/recordings/route.ts
    - src/app/api/recordings/[id]/route.ts
    - src/app/api/recordings/[id]/status/route.ts
    - src/app/api/recordings/[id]/transcript/route.ts
    - src/app/api/projects/route.ts
    - src/hooks/use-recordings.ts
    - src/hooks/use-projects.ts
  modified:
    - next.config.ts
    - src/app/api/recordings/__tests__/route.test.ts
    - src/hooks/__tests__/use-recordings.test.ts

key-decisions:
  - "Used process.cwd() for schema.sql path resolution instead of __dirname (unreliable with bundlers)"
  - "Schema creates projects table before recordings table to satisfy FK constraint ordering"
  - "serverExternalPackages in next.config.ts for better-sqlite3 native addon support"

patterns-established:
  - "SQLite singleton: getDb() function with lazy init, WAL mode, FK enforcement"
  - "API route proxy: Forward FormData to FastAPI without setting Content-Type (boundary auto-generated)"
  - "Status mapping: Backend statuses (pending/completed/failed) mapped to local enum (processing/ready/error)"
  - "Polling pattern: refetchInterval returns 3000ms while processing, false on ready/error"

requirements-completed: [REC-04, STT-01, STT-04]

duration: 9min
completed: 2026-03-12
---

# Phase 1 Plan 2: Data Layer and API Proxy Summary

**SQLite database with better-sqlite3, Next.js API route proxies to FastAPI, and TanStack Query hooks with 3s status polling**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-11T21:12:06Z
- **Completed:** 2026-03-11T21:20:48Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- SQLite database initializes with recordings and projects tables, WAL mode, FK enforcement
- API routes proxy uploads to FastAPI backend; unassigned recordings saved locally only
- TanStack Query hooks provide data fetching with status polling every 3s, auto-stop on completion
- 11 tests passing (5 API route tests + 6 hook tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Set up SQLite database and API routes** - `4de1e738` (feat)
2. **Task 2: Create TanStack Query hooks for recordings and projects** - `943df6a6` (feat)

## Files Created/Modified
- `src/lib/db/index.ts` - better-sqlite3 singleton with WAL mode, schema initialization
- `src/lib/db/schema.sql` - recordings and projects table definitions
- `src/lib/db/recordings.ts` - Recording CRUD with snake_case to camelCase mapping
- `src/lib/db/projects.ts` - Project CRUD with crypto.randomUUID()
- `src/lib/api/client.ts` - Fetch wrapper with typed error handling (ApiError class)
- `src/app/api/recordings/route.ts` - GET list + POST upload with local save and FastAPI proxy
- `src/app/api/recordings/[id]/route.ts` - GET/PATCH single recording
- `src/app/api/recordings/[id]/status/route.ts` - GET status with backend status mapping
- `src/app/api/recordings/[id]/transcript/route.ts` - GET transcript proxy to FastAPI
- `src/app/api/projects/route.ts` - GET/POST projects from local SQLite
- `src/hooks/use-recordings.ts` - TanStack Query hooks for recordings with polling
- `src/hooks/use-projects.ts` - TanStack Query hooks for projects
- `next.config.ts` - Added serverExternalPackages for better-sqlite3

## Decisions Made
- Used `process.cwd()` for schema.sql path resolution instead of `__dirname` (unreliable with Next.js bundlers)
- Schema creates projects table before recordings for FK constraint ordering
- Added `serverExternalPackages: ["better-sqlite3"]` to next.config.ts for native addon support
- Status mapping: backend `pending/processing` -> `processing`, `completed/ready` -> `ready`, `failed/error` -> `error`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed schema table ordering for FK constraint**
- **Found during:** Task 1 (SQLite setup)
- **Issue:** Existing scaffold had recordings table defined before projects table, but recordings.project_id has FK to projects(id)
- **Fix:** Reordered schema.sql to create projects table first
- **Files modified:** src/lib/db/schema.sql
- **Verification:** Build passes, CREATE TABLE IF NOT EXISTS handles idempotency
- **Committed in:** 4de1e738 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed __dirname path resolution for schema.sql**
- **Found during:** Task 1 (SQLite setup)
- **Issue:** Existing scaffold used `__dirname` to locate schema.sql, which is unreliable with Next.js/Turbopack bundling
- **Fix:** Changed to `resolve(process.cwd(), "src/lib/db/schema.sql")`
- **Files modified:** src/lib/db/index.ts
- **Verification:** Build passes, schema initializes correctly
- **Committed in:** 4de1e738 (Task 1 commit)

**3. [Rule 3 - Blocking] Added serverExternalPackages for better-sqlite3**
- **Found during:** Task 1 (SQLite setup)
- **Issue:** better-sqlite3 is a native Node.js addon; Next.js build would fail without marking it as external
- **Fix:** Added `serverExternalPackages: ["better-sqlite3"]` to next.config.ts
- **Files modified:** next.config.ts
- **Verification:** `npm run build` succeeds with all API routes compiled
- **Committed in:** 4de1e738 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (2 bug fixes, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- Vitest `vi.mock("fs")` required special handling for the `default` export in CJS/ESM interop; resolved using `vi.mock(import("fs"))` with `importOriginal` and explicit `default` property

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data layer complete: recordings and projects can be created, queried, updated
- API proxy layer ready: uploads proxy to FastAPI at BACKEND_URL (default http://localhost:8000)
- Hooks ready for UI consumption: useRecordings, useRecordingStatus, useUploadRecording, useAssignProject
- Ready for Plan 03 (Recording Hub UI) and Plan 04 (Transcript Display)

## Self-Check: PASSED
- All 15 key files verified present on disk
- Commit 4de1e738 (Task 1) verified in git log
- Commit 943df6a6 (Task 2) verified in git log
- Build passes (`npm run build`)
- All 11 tests pass (5 API route + 6 hook tests)

---
*Phase: 01-recording-and-transcription-pipeline*
*Completed: 2026-03-12*
