# Phase 3: Task Management - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can manage tasks through full CRUD operations in both list and Kanban views. Tasks can be created manually or arrive via promotion from AI-extracted outcomes (Phase 2). Schema must be extended with priority, due date, assignee, and tags fields. The sidebar Tasks placeholder activates with a /tasks route.

</domain>

<decisions>
## Implementation Decisions

### Task Creation & Fields
- "+ New Task" button at top of task list/Kanban opens a modal dialog for creation
- Only title is required — status defaults to "To Do"
- Priority, due date, assignee, tags are all optional (settable later via detail panel)
- Same "+ New Task" button works in both List and Kanban views; on Kanban, new tasks default to "To Do" column
- Schema extension needed: add priority (Low/Medium/High), due_date, assignee, tags columns to tasks table

### Task Statuses
- Three statuses: To Do, In Progress, Done
- Current schema default 'todo' aligns — add 'in_progress' and 'done'

### Priority Levels
- Three levels: Low, Medium, High
- Color-coded badges: green (Low), amber (Medium), red (High)
- Default to Medium when not explicitly set

### List View
- Columns: Title, Status, Priority, Due Date (four columns)
- Status tab bar filtering: All / To Do / In Progress / Done (consistent with Recording Hub tab pattern)
- Text search bar for filtering by task title
- Default sort: priority descending (High first), then by created date within each priority
- Clicking a task row opens a detail side panel/modal

### Kanban Board
- Three columns: To Do, In Progress, Done
- Drag-and-drop cards between columns updates task status
- Cards show: title + priority badge (colored dot) + due date if set
- Compact, clean cards — Linear-style density
- Clicking a card opens the same detail panel as the list view

### View Toggle
- Tab bar labeled "List" and "Board" above the content area
- Consistent with Recording Hub tab pattern
- Remembers last selection

### Task Detail Panel
- Side panel opens on task click (from either list or Kanban)
- Inline editable fields — click to edit title, dropdowns for status/priority, date picker for due date
- Changes save automatically (no explicit Save button)
- For promoted tasks: subtle "Source" section at bottom showing recording name + timestamp (backlink from Phase 2)

### Task Deletion
- Delete button in detail panel with confirmation dialog before deleting
- Simple and safe — no swipe gestures or hidden menus

### Claude's Discretion
- Drag-and-drop library choice for Kanban (dnd-kit, react-beautiful-dnd, etc.)
- Detail panel animation and positioning (right panel vs centered modal)
- Kanban column header design and card spacing
- Auto-save debounce timing for inline edits
- Empty state messaging for task list (no tasks yet)
- Tags implementation (free-text vs predefined, storage format)
- Assignee field format (free-text name for FYP scope)
- How column sort indicators look

</decisions>

<specifics>
## Specific Ideas

- Tab bar for List/Board toggle matches the Recording Hub's tab pattern — keeps UI language consistent
- Detail panel behavior like Linear's side panel — click a row/card, panel slides in, edit inline
- Promoted tasks retain subtle source section to show the Record-to-Tasks pipeline during FYP demo
- Priority-then-date sort surfaces urgent work first — useful for demo scenarios
- Compact Kanban cards keep the board scannable without visual overload

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/components/ui/table.tsx` — Table component used in Recording Hub, reusable for task list
- `src/components/ui/tabs.tsx` — Tab component for status filtering and List/Board toggle
- `src/components/ui/badge.tsx` — Badge component for status and priority indicators
- `src/components/ui/card.tsx` — Card component for Kanban cards
- `src/components/ui/input.tsx` — Input component for search bar and inline editing
- `src/components/ui/select.tsx` — Select component for priority/status dropdowns
- `src/components/ui/button.tsx` — Button component for "+ New Task" and actions
- `src/components/ui/skeleton.tsx` — Skeleton for loading states
- `src/lib/db/tasks.ts` — Existing task CRUD functions (createTask, getTask) — needs extension for update, delete, list, filter
- `src/lib/db/schema.sql` — Tasks table exists but needs priority, due_date, assignee, tags columns
- `src/hooks/use-recordings.ts` — Pattern for TanStack Query hooks to follow for tasks

### Established Patterns
- shadcn/ui component library with Tailwind CSS and oklch colors
- TanStack Query for data fetching with polling
- Next.js API routes for all data operations
- SQLite (better-sqlite3) for frontend metadata storage
- `sonner` for toast notifications
- Space Grotesk headings + Inter body text (Phase 2.1)
- Indigo primary theme with slate neutrals (Phase 2.1)
- Tab bar filtering pattern from Recording Hub (All/Unassigned/Processing/Ready)

### Integration Points
- `src/components/app-sidebar.tsx` — Tasks nav item needs activation (currently disabled with `url: "#"`)
- `src/app/(dashboard)/` — New `/tasks` route needed under dashboard layout
- `src/lib/db/tasks.ts` — Extend with updateTask, deleteTask, listTasks, filterTasks
- `src/lib/db/schema.sql` — ALTER tasks table or update CREATE TABLE with new columns
- `src/hooks/` — New `use-tasks.ts` hook for task data fetching
- `src/types/outcome.ts` — Task type needs extension with priority, dueDate, assignee, tags
- Dashboard stat card "Tasks Created" (Phase 2.1) should reflect actual task count

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-task-management*
*Context gathered: 2026-03-14*

