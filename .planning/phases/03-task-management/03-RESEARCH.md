# Phase 3: Task Management - Research

**Researched:** 2026-03-14
**Domain:** Task CRUD, list/Kanban views, drag-and-drop, SQLite schema extension
**Confidence:** HIGH

## Summary

Phase 3 implements full task management with CRUD operations, a sortable/filterable list view, and a drag-and-drop Kanban board. The project already has a `tasks` table in SQLite with basic fields (id, title, detail, status, source links) and existing `createTask`/`getTask` functions from Phase 2's promotion flow. This phase extends that schema with priority, due_date, assignee, and tags columns, adds update/delete/list operations, and builds two view modes (List and Kanban) accessible via a new `/tasks` route.

The existing codebase provides strong patterns to follow: TanStack Query hooks for data fetching (see `use-recordings.ts`), Next.js API routes for CRUD (see recordings API), shadcn/ui components (Table, Tabs, Badge, Card, Sheet), and the Recording Hub's tab-based filtering pattern. The main new dependency is `@dnd-kit/core` + `@dnd-kit/sortable` for Kanban drag-and-drop.

**Primary recommendation:** Use the stable `@dnd-kit/core` (v6.x) + `@dnd-kit/sortable` packages for Kanban drag-and-drop. Follow the Recording Hub pattern exactly for list view structure. Use the existing Sheet component for the task detail side panel.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- "+ New Task" button at top of task list/Kanban opens a modal dialog for creation
- Only title is required -- status defaults to "To Do"
- Priority, due date, assignee, tags are all optional (settable later via detail panel)
- Same "+ New Task" button works in both List and Kanban views; on Kanban, new tasks default to "To Do" column
- Schema extension needed: add priority (Low/Medium/High), due_date, assignee, tags columns to tasks table
- Three statuses: To Do, In Progress, Done (values: 'todo', 'in_progress', 'done')
- Three priority levels: Low, Medium, High -- color-coded badges: green (Low), amber (Medium), red (High) -- default to Medium
- List view columns: Title, Status, Priority, Due Date (four columns)
- Status tab bar filtering: All / To Do / In Progress / Done (consistent with Recording Hub tab pattern)
- Text search bar for filtering by task title
- Default sort: priority descending (High first), then by created date within each priority
- Clicking a task row opens a detail side panel/modal
- Kanban: Three columns: To Do, In Progress, Done
- Drag-and-drop cards between columns updates task status
- Kanban cards show: title + priority badge (colored dot) + due date if set
- Compact, clean cards -- Linear-style density
- Clicking a card opens the same detail panel as the list view
- Tab bar labeled "List" and "Board" above the content area -- remembers last selection
- Task detail side panel opens on click (from either view)
- Inline editable fields -- click to edit title, dropdowns for status/priority, date picker for due date
- Changes save automatically (no explicit Save button)
- For promoted tasks: subtle "Source" section showing recording name + timestamp
- Delete button in detail panel with confirmation dialog before deleting

### Claude's Discretion
- Drag-and-drop library choice for Kanban (dnd-kit, react-beautiful-dnd, etc.)
- Detail panel animation and positioning (right panel vs centered modal)
- Kanban column header design and card spacing
- Auto-save debounce timing for inline edits
- Empty state messaging for task list (no tasks yet)
- Tags implementation (free-text vs predefined, storage format)
- Assignee field format (free-text name for FYP scope)
- How column sort indicators look

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TASK-01 | User can create, read, update, and delete tasks | Schema extension + API routes + existing CRUD pattern from recordings |
| TASK-02 | Tasks have title, status, priority, due date, assignee, tags | Schema ALTER adds priority, due_date, assignee, tags columns |
| TASK-03 | Tasks display in a sortable/filterable list view | Recording Hub tab/filter pattern + Table component reuse |
| TASK-04 | Tasks display in a drag-and-drop Kanban board view | @dnd-kit/core + @dnd-kit/sortable for DnD |
| TASK-05 | Dragging a Kanban card updates task status | DnD onDragEnd handler + PATCH /api/tasks/[id] |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @dnd-kit/core | ^6.3.1 | Drag-and-drop engine | Stable, mature (2294 dependents), framework for custom DnD |
| @dnd-kit/sortable | ^10.0.0 | Sortable preset for reorderable lists | Required for sorting items within/across Kanban columns |
| @dnd-kit/utilities | ^3.2.2 | CSS transform utilities | Helper for DragOverlay positioning |

### Already Installed (use as-is)
| Library | Purpose | Phase 3 Use |
|---------|---------|-------------|
| @tanstack/react-query ^5 | Data fetching + mutations | `use-tasks.ts` hook for all task operations |
| better-sqlite3 ^12 | SQLite database | Schema extension, task CRUD queries |
| shadcn/ui (base-ui) | UI components | Table, Tabs, Badge, Card, Sheet, Input, Select, Button |
| date-fns ^4 | Date formatting | Due date display and formatting |
| sonner ^2 | Toast notifications | Success/error feedback on task operations |
| zod ^4 | Schema validation | Validate task creation/update payloads |
| zustand ^5 | Client state | Remember List/Board view toggle preference |
| lucide-react | Icons | Task-related icons (Plus, GripVertical, Calendar, etc.) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @dnd-kit/core | react-beautiful-dnd | react-beautiful-dnd is archived/unmaintained since 2024; dnd-kit is actively maintained |
| @dnd-kit/core | @dnd-kit/react (v0.3.2) | @dnd-kit/react is pre-1.0, only 32 dependents -- too experimental for FYP deadline |
| Sheet (side panel) | Dialog (centered modal) | Sheet matches Linear-style side panel UX per user decision |

**Installation:**
```bash
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  app/(dashboard)/tasks/
    page.tsx                  # /tasks route - TaskPage component
  app/api/tasks/
    route.ts                  # GET (list+filter), POST (create)
  app/api/tasks/[id]/
    route.ts                  # GET, PATCH (update), DELETE
  components/task/
    task-page.tsx             # Main page: view toggle + content
    task-list-view.tsx        # Table-based list view with tabs
    task-kanban-view.tsx      # Kanban board with DnD
    task-kanban-column.tsx    # Single Kanban column (droppable)
    task-kanban-card.tsx      # Single Kanban card (draggable/sortable)
    task-detail-panel.tsx     # Sheet side panel for viewing/editing
    task-create-dialog.tsx    # Modal dialog for new task creation
    task-priority-badge.tsx   # Color-coded priority badge component
  hooks/
    use-tasks.ts              # TanStack Query hooks: useTasks, useCreateTask, useUpdateTask, useDeleteTask
  lib/db/
    tasks.ts                  # Extended: updateTask, deleteTask, listTasks (add to existing)
    schema.sql                # ALTER TABLE or updated CREATE TABLE
  types/
    outcome.ts                # Extended Task type with priority, dueDate, assignee, tags
```

### Pattern 1: API Route CRUD (follow recordings pattern)
**What:** Next.js route handlers that call SQLite DB functions directly
**When to use:** All task data operations
**Example:**
```typescript
// src/app/api/tasks/route.ts -- follows src/app/api/recordings/route.ts pattern
import { NextRequest, NextResponse } from "next/server"
import { listTasks, createTask } from "@/lib/db/tasks"

export async function GET(request: NextRequest) {
  const status = request.nextUrl.searchParams.get("status")
  const search = request.nextUrl.searchParams.get("search")
  const tasks = listTasks({ status, search })
  return NextResponse.json(tasks)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  // validate with zod, create task, return 201
  const task = createTask(body)
  return NextResponse.json(task, { status: 201 })
}
```

### Pattern 2: TanStack Query Hooks (follow use-recordings.ts pattern)
**What:** Custom hooks wrapping useQuery/useMutation with query invalidation
**When to use:** All frontend data fetching/mutation for tasks
**Example:**
```typescript
// src/hooks/use-tasks.ts -- follows src/hooks/use-recordings.ts pattern
export function useTasks(filters?: TaskFilters) {
  const params = new URLSearchParams()
  if (filters?.status) params.set("status", filters.status)
  if (filters?.search) params.set("search", filters.search)
  const qs = params.toString()

  return useQuery({
    queryKey: ["tasks", filters ?? "all"],
    queryFn: () => apiClient.get<Task[]>(`/api/tasks${qs ? `?${qs}` : ""}`),
  })
}

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: UpdateTaskInput) =>
      apiClient.patch<Task>(`/api/tasks/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}
```

### Pattern 3: Kanban DnD with @dnd-kit
**What:** DndContext wrapping sortable columns with SortableContext per column
**When to use:** Kanban board view
**Example:**
```typescript
// Core Kanban structure
import { DndContext, DragOverlay, closestCorners } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"

function KanbanBoard({ tasks }: { tasks: Task[] }) {
  const columns = {
    todo: tasks.filter(t => t.status === "todo"),
    in_progress: tasks.filter(t => t.status === "in_progress"),
    done: tasks.filter(t => t.status === "done"),
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over) return
    // Determine target column from over.id or over.data
    // Call updateTask mutation with new status
  }

  return (
    <DndContext collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
      {Object.entries(columns).map(([status, items]) => (
        <KanbanColumn key={status} status={status} tasks={items} />
      ))}
      <DragOverlay>{/* Render active card clone */}</DragOverlay>
    </DndContext>
  )
}
```

### Pattern 4: Sheet Side Panel (reuse existing Sheet component)
**What:** Right-sliding sheet panel for task detail/editing
**When to use:** Click on task row or Kanban card
**Example:**
```typescript
// Uses existing src/components/ui/sheet.tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"

function TaskDetailPanel({ task, open, onClose }: Props) {
  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="right" className="sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{task.title}</SheetTitle>
        </SheetHeader>
        {/* Inline editable fields */}
      </SheetContent>
    </Sheet>
  )
}
```

### Pattern 5: Schema Migration via CREATE TABLE IF NOT EXISTS
**What:** SQLite schema uses CREATE TABLE IF NOT EXISTS, so add new columns via separate ALTER TABLE statements
**When to use:** Schema extension for priority, due_date, assignee, tags
**Example:**
```sql
-- Append to schema.sql after existing CREATE TABLE tasks
-- ALTER TABLE is idempotent when wrapped in a try/catch in the DB init
-- Or: drop and recreate tasks table if no production data exists (FYP project)
ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium';
ALTER TABLE tasks ADD COLUMN due_date TEXT;
ALTER TABLE tasks ADD COLUMN assignee TEXT;
ALTER TABLE tasks ADD COLUMN tags TEXT NOT NULL DEFAULT '[]';
```

### Anti-Patterns to Avoid
- **Do not use SortableContext without unique string IDs:** dnd-kit requires stable unique identifiers. Use task.id directly.
- **Do not mutate query cache directly for DnD:** Use optimistic updates via TanStack Query's `onMutate` to update local state immediately, then let `onSettled` refetch.
- **Do not use `useEffect` for auto-save:** Use `useMutation` with debounced input. The mutation fires on field blur or after a debounce timer (300-500ms).
- **Do not add a Dialog component from scratch:** The project uses `@base-ui/react` Dialog under the hood for Sheet. Use the same base for the creation dialog, or add shadcn dialog component via CLI.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop | Custom pointer event handlers | @dnd-kit/core + @dnd-kit/sortable | Accessibility (keyboard DnD), touch support, collision detection, overlay rendering |
| Optimistic updates | Manual cache manipulation | TanStack Query onMutate/onError/onSettled | Rollback on error, cache consistency, refetch coordination |
| Date picker | Custom calendar widget | Native `<input type="date">` or existing shadcn component | FYP scope -- native date input is sufficient |
| Debounced auto-save | Custom setTimeout management | useDeferredValue (already used in project) or simple setTimeout in mutation wrapper | Timer cleanup, React 19 integration |
| UUID generation | Custom ID generator | `crypto.randomUUID()` | Already used in project for recording IDs |

**Key insight:** The project has strong existing patterns (recordings CRUD, TanStack Query hooks, tab filtering). Following these patterns reduces implementation risk and keeps the codebase consistent.

## Common Pitfalls

### Pitfall 1: SQLite ALTER TABLE for existing data
**What goes wrong:** ALTER TABLE ADD COLUMN fails silently or causes issues if column already exists
**Why it happens:** Schema.sql runs on every DB init via `db.exec(schema)`. ALTER TABLE errors on re-run.
**How to avoid:** Wrap ALTER TABLE statements in try/catch, or check if column exists before altering. Alternatively, since this is an FYP project with no production data, update the CREATE TABLE statement directly and delete the existing DB file.
**Warning signs:** "duplicate column name" errors in console

### Pitfall 2: DnD collision detection with sparse columns
**What goes wrong:** Cannot drop into an empty Kanban column
**Why it happens:** Default collision detection requires overlap with existing items. Empty columns have no sortable items.
**How to avoid:** Use `closestCorners` collision detection strategy (not `closestCenter`). Also ensure each column itself is a droppable target (not just the items within it).
**Warning signs:** Cards cannot be moved to empty columns during testing

### Pitfall 3: Stale query cache after DnD status change
**What goes wrong:** After dragging a card, the list view shows stale data
**Why it happens:** Kanban and list share the same `["tasks"]` query key but DnD optimistic update only modifies local state.
**How to avoid:** Invalidate `["tasks"]` query key in onSettled of the update mutation. Use same query key structure across both views.
**Warning signs:** Switching between List and Board shows different task states

### Pitfall 4: Sheet component controlled state
**What goes wrong:** Sheet panel doesn't close or opens multiple times
**Why it happens:** The base-ui Dialog/Sheet requires controlled `open` state. Uncontrolled usage leads to stale references.
**How to avoid:** Manage `selectedTaskId` state at the page level. Pass `open={!!selectedTaskId}` and `onOpenChange` to Sheet.
**Warning signs:** Panel flickers or requires double-click to close

### Pitfall 5: Tags stored as JSON string in SQLite
**What goes wrong:** Tags column stores `'[]'` default but comparisons fail
**Why it happens:** SQLite has no native JSON array type. Tags stored as JSON string need parse/stringify on read/write.
**How to avoid:** Always `JSON.parse()` tags in `rowToTask()` and `JSON.stringify()` in write operations. Use `TEXT NOT NULL DEFAULT '[]'` in schema.
**Warning signs:** Tags appear as `"[]"` string instead of empty array in UI

## Code Examples

### Task Type Extension
```typescript
// src/types/outcome.ts -- extend existing Task interface
export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type TaskPriority = 'low' | 'medium' | 'high'

export interface Task {
  id: string
  title: string
  detail: string
  status: TaskStatus
  priority: TaskPriority
  dueDate: string | null
  assignee: string | null
  tags: string[]
  sourceOutcomeId: string | null
  sourceRecordingId: string | null
  backlink: string | null
  createdAt: string
  updatedAt: string
}
```

### Priority Badge Component
```typescript
// Reuses existing Badge component with color variants
const PRIORITY_CONFIG = {
  high: { label: "High", className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
  medium: { label: "Medium", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
  low: { label: "Low", className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" },
} as const
```

### DB listTasks with filtering
```typescript
export function listTasks(filters?: {
  status?: string | null
  search?: string | null
}): Task[] {
  const db = getDb()
  let sql = "SELECT * FROM tasks WHERE 1=1"
  const params: unknown[] = []

  if (filters?.status) {
    sql += " AND status = ?"
    params.push(filters.status)
  }
  if (filters?.search) {
    sql += " AND title LIKE ?"
    params.push(`%${filters.search}%`)
  }

  sql += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at DESC"

  const rows = db.prepare(sql).all(...params) as TaskRow[]
  return rows.map(rowToTask)
}
```

## Discretion Recommendations

Based on research, here are recommendations for areas left to Claude's discretion:

| Area | Recommendation | Rationale |
|------|---------------|-----------|
| DnD library | @dnd-kit/core + @dnd-kit/sortable (v6.x stable) | Mature, accessible, 2294+ dependents, not react-beautiful-dnd (archived) |
| Detail panel | Right-side Sheet (existing component) | Matches Linear-style UX, Sheet component already exists in project |
| Auto-save debounce | 500ms setTimeout on field blur | Simple, no extra library needed; useDeferredValue already in project for search |
| Empty state | Centered illustration-free message with "+ New Task" CTA button | Consistent with existing "No recordings found" pattern |
| Tags storage | JSON array string in SQLite TEXT column, free-text comma-separated input | Simplest for FYP; no predefined tag taxonomy needed |
| Assignee format | Free-text string input | FYP scope -- no user management system |
| Sort indicators | Small chevron icon next to active sort column header | Lightweight, consistent with table conventions |
| Kanban card spacing | 8px gap (gap-2), 12px padding per card | Matches Linear density |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-beautiful-dnd | @dnd-kit/core | 2024 (rbd archived) | dnd-kit is the standard React DnD library now |
| @dnd-kit/core v5 | @dnd-kit/core v6 | 2024 | Minor API changes, stable |
| Custom fetch + setState | TanStack Query mutations | Already adopted | Optimistic updates, cache invalidation built-in |

**Deprecated/outdated:**
- react-beautiful-dnd: Archived by Atlassian, no longer maintained. Do not use.
- @dnd-kit/react (v0.3.2): Pre-1.0 experimental rewrite. Too risky for FYP deadline. Use @dnd-kit/core v6.x.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.x + happy-dom + @testing-library/react |
| Config file | vitest.config.ts |
| Quick run command | `npm test` |
| Full suite command | `npm test` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TASK-01 | CRUD operations via API routes | unit | `npx vitest run src/app/api/tasks/__tests__/route.test.ts` | No - Wave 0 |
| TASK-02 | Task fields (priority, due_date, assignee, tags) stored and returned | unit | `npx vitest run src/app/api/tasks/__tests__/route.test.ts` | No - Wave 0 |
| TASK-03 | List view filtering by status and search | unit | `npx vitest run src/app/api/tasks/__tests__/route.test.ts` | No - Wave 0 |
| TASK-04 | Kanban board renders columns with tasks | unit | `npx vitest run src/components/task/__tests__/task-kanban-view.test.tsx` | No - Wave 0 |
| TASK-05 | Drag updates task status | unit | `npx vitest run src/components/task/__tests__/task-kanban-view.test.tsx` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `npm test`
- **Per wave merge:** `npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/app/api/tasks/__tests__/route.test.ts` -- covers TASK-01, TASK-02, TASK-03 (API CRUD + filtering)
- [ ] `src/components/task/__tests__/task-kanban-view.test.tsx` -- covers TASK-04, TASK-05 (Kanban rendering + DnD behavior)
- [ ] No new framework install needed -- Vitest + Testing Library already configured

## Open Questions

1. **Dialog component for task creation**
   - What we know: Project has Sheet (base-ui Dialog) but no standalone Dialog/AlertDialog component
   - What's unclear: Whether to use Sheet for creation too, or add a shadcn Dialog component
   - Recommendation: Add shadcn Dialog component via CLI (`npx shadcn@latest add dialog`) for the creation modal and confirmation dialogs. Sheet for detail panel, Dialog for creation/deletion confirmation.

2. **Existing promoted tasks in DB**
   - What we know: Phase 2 already creates tasks via promotion (createTask in tasks.ts). These tasks lack priority/due_date/assignee/tags columns.
   - What's unclear: Whether existing promoted tasks will break after schema migration
   - Recommendation: Use DEFAULT values in ALTER TABLE so existing rows get sensible defaults (priority='medium', tags='[]', others NULL).

## Sources

### Primary (HIGH confidence)
- Project codebase: src/lib/db/schema.sql, src/lib/db/tasks.ts, src/hooks/use-recordings.ts, src/components/recording/recording-hub.tsx -- direct code inspection
- Project codebase: src/components/ui/sheet.tsx, src/components/ui/badge.tsx -- existing UI components
- Project codebase: src/app/api/recordings/route.ts, src/app/api/recordings/[id]/route.ts -- API route patterns
- [@dnd-kit npm](https://www.npmjs.com/package/@dnd-kit/core) -- v6.3.1, 2294 dependents
- [dnd-kit official docs](https://dndkit.com/) -- framework-agnostic toolkit with React hooks

### Secondary (MEDIUM confidence)
- [LogRocket Kanban tutorial](https://blog.logrocket.com/build-kanban-board-dnd-kit-react/) -- DndContext + SortableContext pattern for Kanban
- [Puck blog - Top 5 DnD libraries 2026](https://puckeditor.com/blog/top-5-drag-and-drop-libraries-for-react) -- dnd-kit ecosystem status
- [shadcn/dnd-kit/tailwind Kanban example](https://github.com/Georgegriff/react-dnd-kit-tailwind-shadcn-ui) -- shadcn + dnd-kit integration reference

### Tertiary (LOW confidence)
- @dnd-kit/react v0.3.2 status -- only from npm search, flagged as experimental/pre-1.0

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - @dnd-kit/core is mature and well-documented; all other libs already in project
- Architecture: HIGH - follows existing project patterns exactly (recordings CRUD, TanStack Query, shadcn)
- Pitfalls: HIGH - based on direct code inspection of schema.sql, dnd-kit docs, and SQLite behavior

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable libraries, no fast-moving concerns)
