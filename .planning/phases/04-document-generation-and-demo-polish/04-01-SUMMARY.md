---
phase: 04-document-generation-and-demo-polish
plan: 01
subsystem: api, database, ui
tags: [llm, document-generation, mermaid, prd, sqlite, tanstack-query, fastapi]

requires:
  - phase: 03-task-management
    provides: "Task CRUD patterns, sidebar nav, dashboard stat cards"
provides:
  - "Backend LLM endpoints for PRD and Mermaid diagram generation"
  - "Frontend SQLite documents table and CRUD module"
  - "API routes for document listing, retrieval, and generation proxy"
  - "TanStack Query hooks for documents"
  - "Sidebar Documents nav activation"
  - "Dashboard 4th stat card: Documents Generated"
affects: [04-02, document-pages, recording-detail]

tech-stack:
  added: []
  patterns: ["synchronous LLM generation via asyncio.to_thread", "proxy-and-store pattern for generation routes"]

key-files:
  created:
    - backend/document_generation.py
    - src/lib/db/documents.ts
    - src/hooks/use-documents.ts
    - src/app/api/documents/route.ts
    - src/app/api/documents/[id]/route.ts
    - src/app/api/recordings/[id]/generate-prd/route.ts
    - src/app/api/recordings/[id]/generate-diagram/route.ts
    - backend/tests/test_document_generation.py
  modified:
    - backend/main.py
    - src/lib/db/schema.sql
    - src/hooks/use-dashboard-stats.ts
    - src/components/app-sidebar.tsx
    - src/app/(dashboard)/page.tsx
    - src/lib/db/documents.test.ts
    - src/app/api/documents/__tests__/route.test.ts

key-decisions:
  - "Synchronous-in-thread LLM generation (Pattern 2) instead of job queue to avoid blocking STT worker"
  - "Documents stored in frontend SQLite, not backend storage, consistent with tasks/outcomes pattern"
  - "Document count fetched via array length from /api/documents for dashboard stat, consistent with outcomes approach"

patterns-established:
  - "Proxy-and-store: Next.js API route calls backend, stores result in frontend SQLite, returns created entity"
  - "Document type validation via zod enum for generate-diagram endpoint"

requirements-completed: [DOC-01, DOC-02]

duration: 11min
completed: 2026-03-15
---

# Phase 4 Plan 01: Document Generation Data Layer Summary

**Backend LLM generation endpoints for PRD and Mermaid diagrams with frontend SQLite CRUD, API routes, TanStack Query hooks, sidebar activation, and dashboard stat card**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-15T09:45:27Z
- **Completed:** 2026-03-15T09:56:29Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Backend document_generation.py with generate_prd and generate_diagram functions using LLM prompts from research
- Two new FastAPI endpoints: POST /recordings/{id}/generate-prd and POST /recordings/{id}/generate-diagram
- Frontend documents table in schema.sql with type constraint (prd, user_flow, erd)
- Full CRUD module (createDocument, getDocument, listDocuments, countDocuments) following tasks.ts pattern
- Four API routes: document list, single document, PRD generation proxy, diagram generation proxy
- TanStack Query hooks: useDocuments, useDocument, useGeneratePrd, useGenerateDiagram with toast notifications
- Sidebar Documents nav item activated with /documents link
- Dashboard expanded to 4 stat cards with Documents Generated
- All Wave 0 test stubs upgraded to real passing tests (CRUD + API routes)

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend generation endpoints and frontend data layer** - `134c11a` (feat)
2. **Task 2: TanStack Query hooks, sidebar activation, and dashboard stat card** - `50f08d7` (feat)

## Files Created/Modified
- `backend/document_generation.py` - LLM generation functions with PRD, user flow, and ERD prompts
- `backend/main.py` - Two new POST endpoints for document generation
- `backend/tests/test_document_generation.py` - Backend unit tests for generation functions
- `src/lib/db/schema.sql` - Documents table with type constraint and FK to recordings
- `src/lib/db/documents.ts` - SQLite CRUD module for documents
- `src/lib/db/documents.test.ts` - CRUD unit tests with mocked DB
- `src/app/api/documents/route.ts` - GET list endpoint with optional type filter
- `src/app/api/documents/[id]/route.ts` - GET single document with 404 handling
- `src/app/api/recordings/[id]/generate-prd/route.ts` - POST proxy to backend, stores result
- `src/app/api/recordings/[id]/generate-diagram/route.ts` - POST proxy with zod type validation
- `src/app/api/documents/__tests__/route.test.ts` - API route tests
- `src/hooks/use-documents.ts` - TanStack Query hooks with mutation toasts
- `src/hooks/use-dashboard-stats.ts` - Added documentsGenerated field and /api/documents query
- `src/components/app-sidebar.tsx` - Documents link activated, removed disabled code branch
- `src/app/(dashboard)/page.tsx` - 4th stat card, updated grid to md:grid-cols-4

## Decisions Made
- Used synchronous-in-thread LLM generation (asyncio.to_thread) instead of job queue -- avoids blocking STT/extraction worker for user-triggered one-shot operations
- Documents stored in frontend SQLite (not backend storage.py) -- consistent with tasks/outcomes pattern where frontend owns metadata
- Document count for dashboard stat uses array length from /api/documents -- consistent with how outcomes are counted, avoids separate count endpoint
- Removed dead disabled-item code branch from sidebar since all nav items are now active

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed sidebar TypeScript error from removed disabled property**
- **Found during:** Task 2 (Sidebar activation)
- **Issue:** After removing `disabled: true` from Documents nav item, TypeScript complained that `item.disabled` does not exist on the nav item type
- **Fix:** Removed the entire disabled conditional branch since no nav items use it anymore
- **Files modified:** src/components/app-sidebar.tsx
- **Verification:** TypeScript compiles without errors
- **Committed in:** 50f08d7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor cleanup -- removed dead code that caused type error. No scope creep.

## Issues Encountered
- Test mock for better-sqlite3 required mocking `./index` (getDb) directly instead of the better-sqlite3 module to avoid migration code running during tests

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Data layer complete: Plan 02 can build document list page (/documents), document detail page (/documents/[id]), and recording detail generate buttons on top of these hooks and API routes
- Mermaid.js npm package still needs to be installed (Plan 02 scope for client-side rendering)
- Backend generation tests should be run with `cd backend && python -m pytest tests/test_document_generation.py -v` when Python environment is available

---
*Phase: 04-document-generation-and-demo-polish*
*Completed: 2026-03-15*

