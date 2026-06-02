---
phase: 03-task-management
verified: 2026-03-14T06:00:00Z
status: human_needed
score: 15/15 must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to /tasks via sidebar, create a task, and verify it appears in the list"
    expected: "Tasks link is active (not disabled), dialog opens, task appears with status 'To Do' and priority 'Medium'"
    why_human: "UI rendering, modal open/close, and list update require visual confirmation in browser"
  - test: "Click a task row, edit status and priority fields in the detail panel"
    expected: "Sheet panel slides open, selects change value on interact, list row badge updates after save"
    why_human: "Auto-save on change and cache invalidation require live browser verification"
  - test: "Switch to Board tab, drag a card from To Do to Done"
    expected: "Kanban board shows three columns, card moves on drop, card reappears in Done column"
    why_human: "Drag-and-drop interaction and optimistic UI update cannot be verified statically"
  - test: "Delete a task via the detail panel delete button"
    expected: "AlertDialog appears, confirming removes the task from list and closes the panel"
    why_human: "Confirmation dialog flow and removal from live list require browser verification"
  - test: "Use text search bar to filter tasks by title"
    expected: "List narrows in real-time as user types, deferred value prevents excessive requests"
    why_human: "Debounced search filtering requires live user interaction to observe"
---

# Phase 03: Task Management Verification Report

**Phase Goal:** Build the task management system with list view, kanban board, CRUD operations, and source linking back to recordings.
**Verified:** 2026-03-14T06:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All truths are drawn directly from the `must_haves` frontmatter across plans 01, 02, and 03.

#### Plan 01 Truths (data layer)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tasks can be created with title only (status defaults to todo, priority defaults to medium) | VERIFIED | `createTask()` in `src/lib/db/tasks.ts` L95-96 sets `priority = data.priority ?? "medium"`, `status TEXT NOT NULL DEFAULT 'todo'` in schema |
| 2 | Tasks can be updated (title, status, priority, due_date, assignee, tags) | VERIFIED | `updateTask()` in `src/lib/db/tasks.ts` L189-249, dynamic SET clauses for all 7 fields |
| 3 | Tasks can be deleted by ID | VERIFIED | `deleteTask()` in `src/lib/db/tasks.ts` L269-273, returns `result.changes > 0` |
| 4 | Tasks can be listed with optional status filter and text search | VERIFIED | `listTasks()` in `src/lib/db/tasks.ts` L154-187, dynamic WHERE clause for status and LIKE search |
| 5 | Tasks sort by priority descending (high first), then created_at descending | VERIFIED | SQL CASE expression in `listTasks()` L180-183: `WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3` |
| 6 | Existing promoted tasks from Phase 2 remain intact after schema migration | VERIFIED | `createTask()` backward-compatible; `src/lib/db/index.ts` L29-41 uses ALTER TABLE IF column missing, preserving existing rows |

#### Plan 02 Truths (list view UI)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7 | User can navigate to /tasks via the sidebar (no longer disabled) | VERIFIED | `app-sidebar.tsx` L21: `{ title: "Tasks", url: "/tasks", icon: CheckSquare }` — no `disabled` field; only Documents is disabled |
| 8 | User can create a task via '+ New Task' button that opens a modal dialog | VERIFIED | `task-list-view.tsx` L149-153 Button calls `onCreateClick`; `task-page.tsx` sets `createDialogOpen` state; `TaskCreateDialog` renders with `open` prop |
| 9 | Tasks display in a sortable table with Title, Status, Priority, Due Date columns | VERIFIED | `task-list-view.tsx` L87-92 TableHead cells: Title, Status, Priority, Due Date |
| 10 | User can filter tasks by status using tab bar (All / To Do / In Progress / Done) | VERIFIED | `task-list-view.tsx` L156-173 Tabs with four STATUS_TABS values; client-side filter at L58-60 |
| 11 | User can search tasks by title via text search bar | VERIFIED | `task-list-view.tsx` L44 `useDeferredValue(query)`; L49 `useTasks({ search: searchFilter })` |
| 12 | Clicking a task row opens a detail side panel with inline-editable fields | VERIFIED | `task-list-view.tsx` L113-114 TableRow `onClick={() => onTaskClick(task)}`; `task-page.tsx` L15-17 sets `selectedTaskId`; `TaskDetailPanel` receives `taskId` |
| 13 | User can edit task fields (title, status, priority, due date, assignee, tags) with auto-save | VERIFIED | `task-detail-panel.tsx` L75-137: all fields have blur/change handlers calling `handleUpdate` which calls `updateTask.mutate()` |
| 14 | User can delete a task via delete button with confirmation dialog | VERIFIED | `task-detail-panel.tsx` L281-289 Button opens AlertDialog; L139-150 `handleDelete` calls `deleteTask.mutate()` with success/close flow |

#### Plan 03 Truths (Kanban board)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 15 | Tasks display in a Kanban board with three columns: To Do, In Progress, Done | VERIFIED | `task-kanban-view.tsx` COLUMNS array L22-26; renders three `TaskKanbanColumn` components |
| 16 | Dragging a card from one column to another updates its status | VERIFIED | `task-kanban-view.tsx` L65-108: `handleDragEnd` determines targetStatus, calls `updateTask.mutate({ id, status: targetStatus })` |
| 17 | Kanban cards show title, priority badge (colored dot), and due date if set | VERIFIED | `task-kanban-card.tsx` L59-69: colored dot (`priorityColors`), title, and conditional due date |
| 18 | Clicking a Kanban card opens the same detail panel as the list view | VERIFIED | `task-kanban-card.tsx` L50-55: `onClick` calls `onTaskClick(task)` when `!isDragging`; same `selectedTaskId` state in `task-page.tsx` |
| 19 | Empty columns accept dropped cards (not just columns with existing cards) | VERIFIED | `task-kanban-column.tsx` L16: `useDroppable({ id: status })` on the column div; `setNodeRef` on `div.min-h-[200px]` |
| 20 | Board tab in view toggle renders the Kanban board | VERIFIED | `task-page.tsx` L40-44: `TabsContent value="board"` renders `<TaskKanbanView ... />` (no placeholder) |

**Score:** 20/20 truths verified (automated checks)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/types/outcome.ts` | TaskStatus, TaskPriority, extended Task, TaskFilters, CreateTaskInput, UpdateTaskInput | VERIFIED | All types present; Task includes sourceHighlightIndex added in Plan 03 |
| `src/lib/db/schema.sql` | tasks table with priority, due_date, assignee, tags columns | VERIFIED | All 4 columns present with defaults |
| `src/lib/db/tasks.ts` | listTasks, updateTask, deleteTask, createTask exports | VERIFIED | All 4 functions exported; 274 lines — fully substantive |
| `src/app/api/tasks/route.ts` | GET (list+filter) and POST (create) endpoints | VERIFIED | Both handlers export with zod validation |
| `src/app/api/tasks/[id]/route.ts` | GET, PATCH, DELETE endpoints | VERIFIED | All 3 handlers export with zod validation and 404 handling |
| `src/hooks/use-tasks.ts` | useTasks, useCreateTask, useUpdateTask, useDeleteTask | VERIFIED | All 4 hooks exported; 77 lines — substantive with cache invalidation and toasts |
| `src/app/(dashboard)/tasks/page.tsx` | Next.js route for /tasks | VERIFIED | 9-line thin route with metadata |
| `src/components/task/task-page.tsx` | TaskPage with List/Board tab toggle | VERIFIED | Full implementation; Board tab renders TaskKanbanView |
| `src/components/task/task-list-view.tsx` | Table with tabs, search, sorting | VERIFIED | 177 lines; all features present |
| `src/components/task/task-create-dialog.tsx` | Modal dialog for new tasks | VERIFIED | 127 lines; title-only required, optional details, Enter key submit |
| `src/components/task/task-detail-panel.tsx` | Sheet with inline editing and delete | VERIFIED | 317 lines; all 7 fields editable, source link, delete with AlertDialog |
| `src/components/task/task-priority-badge.tsx` | Color-coded priority badge | VERIFIED | Red/amber/green per priority |
| `src/components/task/task-kanban-view.tsx` | DndContext-wrapped board | VERIFIED | DndContext, DragOverlay, closestCorners, optimistic update present |
| `src/components/task/task-kanban-column.tsx` | Droppable column | VERIFIED | useDroppable with status as id; SortableContext; min-h-[200px] drop target |
| `src/components/task/task-kanban-card.tsx` | Draggable card | VERIFIED | useSortable with data.status; CSS transform; isDragging opacity |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/hooks/use-tasks.ts` | `/api/tasks` | `apiClient.get/post/patch/delete` | WIRED | L29 `apiClient.get<Task[]>(path)`, L42 `apiClient.post<Task>("/api/tasks", data)`, L58 `apiClient.patch<Task>(\`/api/tasks/${id}\`, ...)`, L71 `apiClient.delete<void>(\`/api/tasks/${id}\`)` |
| `src/app/api/tasks/route.ts` | `src/lib/db/tasks.ts` | direct import | WIRED | L4 `import { listTasks, createTask } from "@/lib/db/tasks"` |
| `src/app/api/tasks/[id]/route.ts` | `src/lib/db/tasks.ts` | direct import | WIRED | L4 `import { getTask, updateTask, deleteTask } from "@/lib/db/tasks"` |
| `src/lib/db/tasks.ts` | `src/lib/db/schema.sql` | SQLite queries against tasks table | WIRED | L98-112 INSERT, L134-143 SELECT, L154-186 SELECT with filters, L243 UPDATE, L271 DELETE |
| `src/components/task/task-list-view.tsx` | `src/hooks/use-tasks.ts` | `useTasks` | WIRED | L20 `import { useTasks }`, L49 `const { data: allTasks = [] } = useTasks(...)` |
| `src/components/task/task-create-dialog.tsx` | `src/hooks/use-tasks.ts` | `useCreateTask` | WIRED | L18 `import { useCreateTask }`, L29 `const createTask = useCreateTask()`, L35 `createTask.mutate(...)` |
| `src/components/task/task-detail-panel.tsx` | `src/hooks/use-tasks.ts` | `useUpdateTask` and `useDeleteTask` | WIRED | L36 `import { useTasks, useUpdateTask, useDeleteTask }`, L47 `useUpdateTask()`, L48 `useDeleteTask()`, L78 `updateTask.mutate(...)`, L141 `deleteTask.mutate(...)` |
| `src/components/app-sidebar.tsx` | `/tasks` | Link href | WIRED | L21 `{ title: "Tasks", url: "/tasks", icon: CheckSquare }` — no disabled property |
| `src/components/task/task-kanban-view.tsx` | `src/hooks/use-tasks.ts` | `useTasks`, `useUpdateTask` | WIRED | L19 `import { useTasks, useUpdateTask }`, L36 `useTasks()`, L37 `useUpdateTask()`, L99 `updateTask.mutate(...)` |
| `src/components/task/task-kanban-view.tsx` | `@dnd-kit/core` | `DndContext`, `closestCorners` | WIRED | L5-13 imports; L120-125 `<DndContext collisionDetection={closestCorners} ...>` |
| `src/components/task/task-page.tsx` | `task-kanban-view.tsx` | Board tab | WIRED | L6 `import { TaskKanbanView }`, L41-44 `<TaskKanbanView ... />` inside Board TabsContent |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TASK-01 | 03-01, 03-02 | User can create, read, update, and delete tasks | SATISFIED | Full CRUD via API routes + hooks + UI dialogs/panels |
| TASK-02 | 03-01 | Tasks have title, status, priority, due date, assignee, and tags | SATISFIED | All 6 fields in schema, Task type, and detail panel |
| TASK-03 | 03-02 | Tasks display in a sortable/filterable list view | SATISFIED | task-list-view.tsx with status tabs, search, 4-column table |
| TASK-04 | 03-03 | Tasks display in a drag-and-drop Kanban board view | SATISFIED | task-kanban-view.tsx with DndContext and 3 columns |
| TASK-05 | 03-03 | Dragging a Kanban card updates task status | SATISFIED | handleDragEnd in task-kanban-view.tsx calls updateTask.mutate with new status |

No orphaned requirements: all 5 TASK requirements are claimed by plans and have implementation evidence.

---

### Anti-Patterns Found

No blocker anti-patterns found.

| File | Pattern | Severity | Finding |
|------|---------|----------|---------|
| All task components | `placeholder=` attributes on Input/Textarea | Info | These are HTML input placeholder attributes (UX hint text), not stub patterns |
| `src/app/api/recordings/__tests__/route.test.ts` | Pre-existing TypeScript error | Info | One TS error in test file — pre-existing, not introduced by Phase 03, does not affect task management functionality |

---

### Human Verification Required

The automated checks pass completely. The following items require a human to open a browser and run the dev server (`npm run dev`) to confirm.

#### 1. Task Creation and List Display

**Test:** Navigate to http://localhost:3000/tasks via the sidebar Tasks link. Click "+ New Task", type a title, press Enter or "Create Task".
**Expected:** Tasks link is active (not greyed out). Dialog opens cleanly. Task appears in list table with status "To Do" and priority "Medium". Toast "Task created" appears.
**Why human:** Modal open/close, form submit, and list refresh require live browser interaction to verify.

#### 2. Detail Panel Inline Editing with Auto-Save

**Test:** Click a task row. In the detail panel, change the Status dropdown to "In Progress" and Priority to "High".
**Expected:** Sheet panel opens from the right. Status and priority selects update immediately and trigger auto-save without a Save button. The list row badge updates after cache invalidation.
**Why human:** Auto-save on change and TanStack Query cache invalidation require live observation.

#### 3. Kanban Board Drag and Drop

**Test:** Switch to the Board tab. Drag a card from the "To Do" column and drop it on "Done".
**Expected:** Board shows three columns with correct task counts. Card lifts with DragOverlay preview, drops into Done column, status updates immediately (optimistic), and server confirms.
**Why human:** Drag-and-drop interaction cannot be verified statically.

#### 4. Delete with Confirmation

**Test:** Open a task detail panel, click the red "Delete Task" button, and confirm in the AlertDialog.
**Expected:** AlertDialog appears ("Delete this task? This action cannot be undone."). Confirming removes the task from list and closes both the dialog and panel. Toast "Task deleted" appears.
**Why human:** Multi-step dialog flow and list removal require live browser interaction.

#### 5. Search Filtering

**Test:** With several tasks in the list, type a partial title in the search bar.
**Expected:** List narrows in real-time, showing only matching tasks. Status tab counts update accordingly. Clearing the search restores all tasks.
**Why human:** Debounced search with deferred value requires real user input to observe the filtering behavior.

---

### Additional Verification Note: Source Linking

Plan 03 added a source link in the detail panel for tasks promoted from recordings. This was not in the original Plan 02 spec but is now present:

- `task-detail-panel.tsx` L263-278: "View in transcript" link renders when `task.sourceRecordingId` is non-null, pointing to `/recordings/{id}?highlight={segmentIndex}`
- `src/app/(dashboard)/recordings/[id]/page.tsx` was updated to accept the `?highlight` query param

This extends TASK-01 with recording traceability. No human test is required specifically for this feature beyond the general detail panel test, but noting it for completeness.

---

## Summary

Phase 03 goal is **fully achieved** per automated code verification. All 20 observable truths are verified, all 15 artifacts are substantive and wired, all 11 key links are confirmed connected, and all 5 TASK requirements (TASK-01 through TASK-05) are satisfied.

The TypeScript compilation passes with zero errors in production code (one pre-existing test file error in `route.test.ts` is not related to this phase's work and was present before Phase 03 began per commit history).

The `human_needed` status reflects that the interactive behaviors — drag-and-drop, auto-save, modal flows — cannot be confirmed without running the dev server. The codebase evidence is strong: no stubs, no orphaned artifacts, no broken wiring.

---

_Verified: 2026-03-14T06:00:00Z_
_Verifier: Claude (gsd-verifier)_

