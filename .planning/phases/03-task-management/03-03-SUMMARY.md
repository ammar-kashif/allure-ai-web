---
phase: 03-task-management
plan: 03
subsystem: ui
tags: [react, dnd-kit, kanban, drag-and-drop, tanstack-query]

requires:
  - phase: 03-task-management
    provides: Task CRUD data layer and list view UI
  - phase: 02.1-ui-overhaul
    provides: Dashboard layout, sidebar, UI component patterns
provides:
  - Kanban board with To Do / In Progress / Done columns
  - Drag-and-drop task status updates via @dnd-kit
  - DragOverlay card preview while dragging
  - Board tab wired into task page toggle
  - Source evidence highlight via URL params
affects: [04-documentation]

tech-stack:
  added: ["@dnd-kit/core", "@dnd-kit/sortable", "@dnd-kit/utilities"]
  patterns: [kanban board with DndContext and closestCorners collision, PointerSensor with distance activation, globalThis DB singleton for HMR]

key-files:
  created:
    - src/components/task/task-kanban-view.tsx
    - src/components/task/task-kanban-column.tsx
    - src/components/task/task-kanban-card.tsx
  modified:
    - src/components/task/task-page.tsx
    - src/components/task/task-list-view.tsx
    - src/components/task/task-detail-panel.tsx
    - src/lib/db/index.ts
    - src/lib/db/tasks.ts
    - src/types/outcome.ts
    - src/app/(dashboard)/recordings/[id]/page.tsx

key-decisions:
  - "PointerSensor with distance:5 activation to distinguish click from drag on kanban cards"
  - "globalThis DB singleton pattern to survive Next.js HMR without connection leaks"
  - "ALTER TABLE migration for columns not added by CREATE TABLE IF NOT EXISTS"
  - "sourceHighlightIndex via LEFT JOIN for task-to-evidence linking"
  - "Client-side status filtering in task-list-view instead of duplicate useTasks queries"

patterns-established:
  - "DndContext + closestCorners + DragOverlay for kanban drag-and-drop"
  - "PointerSensor distance constraint to prevent click-drag conflicts"
  - "URL query param (?highlight=N) for cross-page evidence highlighting"

requirements-completed: [TASK-04, TASK-05]

duration: 8min
completed: 2026-03-14
---

# Phase 03 Plan 03: Kanban Board Summary

**Drag-and-drop Kanban board with @dnd-kit, three status columns, and source evidence linking via URL params**

## Performance

- **Duration:** 8 min (across checkpoint)
- **Started:** 2026-03-13T20:09:00Z
- **Completed:** 2026-03-14T05:17:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Kanban board with To Do / In Progress / Done columns rendering tasks grouped by status
- Drag-and-drop between columns updates task status via useUpdateTask mutation
- DragOverlay shows card clone while dragging for visual feedback
- Board tab in task page wired to render KanbanView (replaced placeholder)
- Source evidence "View source" link navigates to recording page with highlight param
- DB singleton survives Next.js HMR via globalThis pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dnd-kit and build Kanban board with drag-and-drop** - `ce56e70` (feat)
2. **Task 2: Verify complete task management feature end-to-end** - `5f0e923` (fix -- checkpoint bug fixes)

## Files Created/Modified
- `src/components/task/task-kanban-view.tsx` - DndContext-wrapped board with three columns and DragOverlay
- `src/components/task/task-kanban-column.tsx` - Droppable column with SortableContext
- `src/components/task/task-kanban-card.tsx` - Draggable card with title, priority dot, due date
- `src/components/task/task-page.tsx` - Board tab wired to KanbanView
- `src/components/task/task-list-view.tsx` - Single useTasks query with client-side filtering
- `src/components/task/task-detail-panel.tsx` - Source link using Next.js Link with highlight param
- `src/lib/db/index.ts` - globalThis DB singleton + ALTER TABLE migration logic
- `src/lib/db/tasks.ts` - sourceHighlightIndex via LEFT JOIN, getTaskSourceSegmentIndex
- `src/types/outcome.ts` - Added sourceHighlightIndex field to Task type
- `src/app/(dashboard)/recordings/[id]/page.tsx` - URL-based highlight support (?highlight=N)

## Decisions Made
- PointerSensor with distance:5 activation constraint prevents accidental drags when clicking kanban cards
- globalThis DB singleton pattern ensures single connection survives Next.js HMR in dev mode
- ALTER TABLE migration needed because CREATE TABLE IF NOT EXISTS does not modify existing tables
- sourceHighlightIndex added via LEFT JOIN on outcomes for task-to-evidence deep linking
- Client-side status filtering in list view eliminates duplicate useTasks query overhead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DB singleton lost on Next.js HMR**
- **Found during:** Task 2 (Checkpoint verification)
- **Issue:** DB connection re-created on every HMR cycle, causing stale state
- **Fix:** globalThis pattern to persist DB singleton across HMR
- **Files modified:** src/lib/db/index.ts
- **Verification:** Dev server maintains DB state across file saves
- **Committed in:** 5f0e923

**2. [Rule 1 - Bug] Duplicate useTasks queries in task-list-view**
- **Found during:** Task 2 (Checkpoint verification)
- **Issue:** Two separate useTasks hooks causing redundant API calls
- **Fix:** Single query with client-side filtering
- **Files modified:** src/components/task/task-list-view.tsx
- **Committed in:** 5f0e923

**3. [Rule 1 - Bug] Task creation 500 error from missing columns**
- **Found during:** Task 2 (Checkpoint verification)
- **Issue:** CREATE TABLE IF NOT EXISTS does not add columns to existing tables
- **Fix:** ALTER TABLE migration for priority, due_date, assignee, tags columns
- **Files modified:** src/lib/db/index.ts
- **Committed in:** 5f0e923

**4. [Rule 1 - Bug] Kanban card click not opening detail panel**
- **Found during:** Task 2 (Checkpoint verification)
- **Issue:** DndContext capturing all pointer events, preventing click through
- **Fix:** PointerSensor with distance:5 activation constraint
- **Files modified:** src/components/task/task-kanban-view.tsx
- **Committed in:** 5f0e923

**5. [Rule 1 - Bug] View source link broken**
- **Found during:** Task 2 (Checkpoint verification)
- **Issue:** Using backlink string as href instead of proper route
- **Fix:** Next.js Link to /recordings/{id}?highlight={segmentIndex}
- **Files modified:** src/components/task/task-detail-panel.tsx, src/app/(dashboard)/recordings/[id]/page.tsx
- **Committed in:** 5f0e923

**6. [Rule 2 - Missing Critical] sourceHighlightIndex for task-evidence linking**
- **Found during:** Task 2 (Checkpoint verification)
- **Issue:** No way to link from task back to specific evidence segment
- **Fix:** LEFT JOIN on outcomes, added sourceHighlightIndex to Task type
- **Files modified:** src/lib/db/tasks.ts, src/types/outcome.ts
- **Committed in:** 5f0e923

---

**Total deviations:** 6 auto-fixed (5 bugs, 1 missing critical)
**Impact on plan:** All fixes necessary for correct end-to-end task management. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete task management feature delivered (CRUD + list + kanban + detail panel)
- All TASK requirements (01-05) fulfilled across plans 01-03
- Ready for Phase 4 documentation/polish work

## Self-Check: PASSED

- All 10 key files verified present on disk
- Commits ce56e70 and 5f0e923 verified in git log

---
*Phase: 03-task-management*
*Completed: 2026-03-14*

