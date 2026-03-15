---
phase: 04-document-generation-and-demo-polish
plan: 02
subsystem: ui
tags: [mermaid, documents, next.js, react, shadcn, tanstack-query]

requires:
  - phase: 04-document-generation-and-demo-polish
    provides: "Document generation backend endpoints, frontend SQLite CRUD, TanStack Query hooks, API routes"
provides:
  - "Documents list page with type filter tabs at /documents"
  - "Document detail page with PRD prose rendering and Mermaid diagram rendering at /documents/[id]"
  - "Generate PRD button and Generate Diagram dropdown on recording detail page"
  - "MermaidDiagram client component with syntax validation and error fallback"
  - "DocumentTypeBadge component for PRD/User Flow/ERD type display"
  - "Inline PRD and Diagram tabs on recording detail page"
affects: [04-03, demo-polish]

tech-stack:
  added: [mermaid]
  patterns: ["client-side Mermaid rendering with parse validation and error fallback", "inline document tabs on recording detail"]

key-files:
  created:
    - src/app/(dashboard)/documents/page.tsx
    - src/app/(dashboard)/documents/[id]/page.tsx
    - src/components/document/mermaid-diagram.tsx
    - src/components/document/document-type-badge.tsx
  modified:
    - src/app/(dashboard)/recordings/[id]/page.tsx
    - src/hooks/use-documents.ts
    - src/lib/db/documents.ts
    - src/app/api/documents/route.ts
    - src/app/api/recordings/[id]/generate-prd/route.ts
    - src/app/api/recordings/[id]/generate-diagram/route.ts
    - backend/document_generation.py
    - backend/main.py

key-decisions:
  - "Used mermaid.parse() for syntax validation before render, with error fallback showing raw code"
  - "Generate Diagram uses DropdownMenu with User Flow and ERD options"
  - "Inline PRD and Diagram tabs added to recording detail for immediate viewing"
  - "Fixed generation proxy routes to use recording.backendId for correct backend dispatch"

patterns-established:
  - "MermaidDiagram: dynamic import, parse-then-render, cancelled flag for unmount safety"
  - "DocumentTypeBadge: color-coded badges (indigo PRD, teal User Flow, violet ERD)"

requirements-completed: [DOC-01, DOC-02, DOC-03]

duration: 25min
completed: 2026-03-15
---

# Phase 4 Plan 02: Document Generation UI Summary

**Documents list/detail pages with Mermaid diagram rendering, generate PRD/diagram buttons on recording detail, and inline document tabs**

## Performance

- **Duration:** ~25 min (across multiple sessions with checkpoint verification)
- **Started:** 2026-03-15T10:00:00Z
- **Completed:** 2026-03-15T11:25:04Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- Documents list page at /documents with All/PRDs/Diagrams filter tabs and type badges
- Document detail page at /documents/[id] rendering PRD prose or Mermaid SVG diagrams
- MermaidDiagram client component with mermaid.parse() validation, error fallback with raw code display
- Generate PRD button and Generate Diagram dropdown (User Flow/ERD) on recording detail page
- Fixed generation proxy routes to use recording.backendId for correct backend API calls
- Added inline PRD and Diagram tabs on recording detail for immediate document viewing
- Mermaid component tests upgraded from stubs to functional tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Documents list page, detail page, and Mermaid renderer** - `903cb74` (feat)
2. **Task 2: Generate buttons on recording detail page** - `8168e93` (feat)
3. **Task 3: Verify complete document generation flow** - checkpoint:human-verify (approved)

Additional post-checkpoint fixes (by orchestrator):
- `6c2ef06` - fix: generation proxy routes and auto-select diagram type
- `86e6984` - feat: inline PRD and Diagram tabs on recording detail page

## Files Created/Modified
- `src/app/(dashboard)/documents/page.tsx` - Documents list page with type filter tabs
- `src/app/(dashboard)/documents/[id]/page.tsx` - Document detail page with PRD/Mermaid rendering
- `src/components/document/mermaid-diagram.tsx` - Client-side Mermaid renderer with error fallback
- `src/components/document/document-type-badge.tsx` - Type badge component (PRD/User Flow/ERD)
- `src/app/(dashboard)/recordings/[id]/page.tsx` - Generate buttons, inline PRD/Diagram tabs
- `src/hooks/use-documents.ts` - Added useDocumentsByRecording hook
- `src/lib/db/documents.ts` - Added listDocumentsByRecordingId function
- `src/app/api/documents/route.ts` - Added recordingId filter support
- `src/app/api/recordings/[id]/generate-prd/route.ts` - Fixed to use backendId
- `src/app/api/recordings/[id]/generate-diagram/route.ts` - Fixed to use backendId
- `backend/document_generation.py` - Improved prompt templates
- `backend/main.py` - Updated endpoint parameter handling

## Decisions Made
- Used mermaid.parse() for syntax validation before render -- prevents broken SVG output with graceful error fallback
- Generate Diagram uses DropdownMenu with User Flow and ERD options -- better UX than separate buttons
- Fixed generation proxy routes to use recording.backendId -- frontend ID differs from backend ID
- Added inline PRD and Diagram tabs on recording detail -- users can view generated documents without navigating away

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed generation proxy routes to use recording.backendId**
- **Found during:** Post-checkpoint verification
- **Issue:** Generation proxy routes were using the frontend recording ID instead of the backend ID, causing 404 errors when calling backend API
- **Fix:** Updated generate-prd and generate-diagram routes to look up recording.backendId
- **Files modified:** src/app/api/recordings/[id]/generate-prd/route.ts, src/app/api/recordings/[id]/generate-diagram/route.ts
- **Committed in:** 6c2ef06

**2. [Rule 2 - Missing Critical] Added inline PRD and Diagram tabs on recording detail**
- **Found during:** Post-checkpoint verification
- **Issue:** Users had to navigate away from recording detail to view generated documents
- **Fix:** Added Documents tab with inline PRD and Diagram sub-tabs on recording detail page
- **Files modified:** src/app/(dashboard)/recordings/[id]/page.tsx, src/hooks/use-documents.ts, src/lib/db/documents.ts
- **Committed in:** 86e6984

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes improve UX and correctness. No scope creep.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Document generation flow complete end-to-end: generate from recording, view in list, render Mermaid diagrams
- Ready for Plan 03 (demo polish) and Plan 04 (final validation)
- All DOC requirements (DOC-01, DOC-02, DOC-03) satisfied

## Self-Check: PASSED

- All 4 created files verified present on disk
- All 4 commits verified in git log (903cb74, 8168e93, 6c2ef06, 86e6984)

---
*Phase: 04-document-generation-and-demo-polish*
*Completed: 2026-03-15*
