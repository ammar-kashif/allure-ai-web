# Phase 4: Document Generation and Demo Polish - Research

**Researched:** 2026-03-15
**Domain:** LLM-based document generation, Mermaid.js diagram rendering, Next.js full-stack CRUD
**Confidence:** HIGH

## Summary

Phase 4 adds document generation (PRD and Mermaid diagrams) triggered from recording detail pages, a documents list page, document detail pages, and a 4th dashboard stat card. The technical challenge has two halves: (1) backend LLM generation using the existing Phi-4-mini / llama-cpp-python infrastructure, and (2) frontend Mermaid.js client-side rendering plus new CRUD routes following established patterns.

The backend work extends the existing job queue with two new job types ("generate_prd" and "generate_diagram"), reusing the same `app_state.llm.create_chat_completion` pattern from `extraction.py`. The frontend work follows the exact patterns established in Phases 2-3: Next.js API routes with zod validation, better-sqlite3 storage, TanStack Query hooks, and shadcn/ui components.

Mermaid.js (v11.x) must be dynamically imported client-side only (`"use client"` + dynamic import or lazy init) because it requires a browser DOM. The `mermaid.render()` API returns an SVG string that can be set via `dangerouslySetInnerHTML`. Syntax validation is critical since LLM-generated Mermaid can have errors -- use `mermaid.parse()` to validate before rendering and show a fallback with the raw code on failure.

**Primary recommendation:** Reuse the existing extraction pattern end-to-end: backend job queue dispatches generation, frontend polls status, results stored in frontend SQLite. Mermaid rendering is purely client-side via dynamic import of the `mermaid` npm package.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- PRD generation triggered from recording detail page -- "Generate PRD" button alongside existing Outcomes tab
- Auto-selects all outcomes and requirements from that recording -- one-click generation, no cherry-picking
- AI-generated prose using LLM (Phi-4-mini via llama.cpp, same backend as extraction)
- LLM composes a natural language PRD from structured outcome data
- Output rendered as styled markdown in-app -- no download/export in v1
- PRD displays on a dedicated /documents/[id] page after generation
- Mermaid diagram generation triggered from recording detail page -- "Generate Diagram" button (user picks type: User Flow or ERD)
- Two diagram types: User Flow flowchart (from action items/decisions) and ERD (from requirements/entities)
- AI-generated Mermaid syntax -- LLM analyzes outcomes and generates the diagram code
- Rendered as inline SVG using Mermaid.js -- no code block, just the visual diagram
- Each generated diagram saved and viewable on its own /documents/[id] page
- Sidebar "Documents" nav item activated with /documents route
- Documents list page with table: Title, Type (PRD/User Flow/ERD badge), Source Recording, Date Generated
- Type filter tabs: All / PRDs / Diagrams -- consistent with Recording Hub and Task list tab patterns
- Clicking a document navigates to /documents/[id] -- dedicated full-page view
- Back button returns to list
- Add 4th stat card: "Documents Generated" -- completes the pipeline story
- Phase 4 is scoped to document generation only -- no additional demo preparation, seed data, or landing pages

### Claude's Discretion
- LLM prompt engineering for PRD prose and Mermaid syntax generation
- PRD template sections and ordering (Overview, Requirements, Decisions, Action Items, etc.)
- Mermaid diagram styling and node/edge design
- Document detail page layout and typography
- Loading/generating state UX while LLM processes
- Error handling for LLM generation failures or invalid Mermaid syntax
- SQLite schema for documents table (id, type, title, content, source recording, timestamps)
- How "Generate PRD" and "Generate Diagram" buttons are placed on recording detail page
- Mermaid.js integration approach (client-side rendering)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOC-01 | User can generate a PRD from approved outcomes and requirements (template-based) | Backend LLM generation endpoint + PRD prompt engineering + frontend document storage and display |
| DOC-02 | User can generate Mermaid diagrams (user flow flowchart, ERD) from project data | Backend diagram generation endpoint + Mermaid.js client-side rendering + diagram type selection UI |
| DOC-03 | Generated Mermaid renders without syntax errors | Mermaid.parse() pre-validation + error fallback UI + constrained LLM prompting with examples |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mermaid | ^11.13.0 | Client-side Mermaid diagram rendering | Official Mermaid.js library, active development, `render()` API returns SVG string |
| llama-cpp-python | (existing) | LLM inference for PRD and diagram generation | Already loaded in backend as `app_state.llm` |
| better-sqlite3 | ^12.6.2 (existing) | Frontend document metadata storage | Established project pattern |
| zod | ^4.3.6 (existing) | Request validation in API routes | Established in Phase 3 task routes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| TanStack Query | ^5.90.21 (existing) | Data fetching + polling for generation status | Document list, detail, and generation status polling |
| sonner | ^2.0.7 (existing) | Toast notifications for generation success/failure | After generation completes or errors |
| lucide-react | ^0.577.0 (existing) | Icons for generate buttons and document type indicators | FileText, FlowChart, Database icons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mermaid (client-side) | mermaid-cli (server-side) | Server-side requires puppeteer/playwright, heavy dependency -- client-side is simpler and sufficient |
| Raw dangerouslySetInnerHTML | react-markdown with mermaid plugin | Extra dependency, more complexity for rendering just SVG -- direct render is cleaner |

**Installation:**
```bash
npm install mermaid
```

No backend dependencies needed -- llama-cpp-python and the job queue are already in place.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── app/(dashboard)/documents/
│   ├── page.tsx                    # Documents list page
│   └── [id]/
│       └── page.tsx                # Document detail page
├── app/api/documents/
│   ├── route.ts                    # GET (list), POST (create from generation)
│   └── [id]/
│       └── route.ts                # GET (single document)
├── app/api/recordings/[id]/
│   ├── generate-prd/
│   │   └── route.ts                # POST -- trigger PRD generation
│   └── generate-diagram/
│       └── route.ts                # POST -- trigger diagram generation
├── components/document/
│   ├── mermaid-diagram.tsx         # Client-side Mermaid renderer
│   ├── prd-view.tsx                # Styled markdown PRD display
│   └── document-type-badge.tsx     # Type badge (PRD/User Flow/ERD)
├── hooks/
│   └── use-documents.ts            # TanStack Query hooks for documents
└── lib/db/
    └── documents.ts                # SQLite CRUD for documents table
```

### Pattern 1: Backend LLM Generation via Job Queue
**What:** Extend the existing job queue with new job types for document generation. The backend receives a request, fetches outcomes from the job store, builds a prompt, calls `app_state.llm.create_chat_completion()`, and returns the result.
**When to use:** For both PRD and diagram generation.
**Example:**
```python
# In job_queue.py -- add new job types
elif job_type == "generate_prd":
    update_job(job_id, prd_status="processing")
    from document_generation import generate_prd
    content = await asyncio.to_thread(generate_prd, job_id, app_state)
    # Return content to the calling endpoint (or store in job)

# In document_generation.py
def generate_prd(job_id: str, app_state: object) -> str:
    job = get_job(job_id)
    outcomes = job.get("outcomes", [])
    # Build prompt from outcomes
    messages = [
        {"role": "system", "content": PRD_SYSTEM_PROMPT},
        {"role": "user", "content": format_outcomes_for_prd(outcomes)},
    ]
    response = app_state.llm.create_chat_completion(
        messages=messages,
        temperature=0.3,
        max_tokens=4096,
    )
    return response["choices"][0]["message"]["content"]
```

### Pattern 2: Synchronous Backend Generation (Recommended Over Job Queue)
**What:** Since document generation is user-initiated and they wait for the result, use a synchronous approach: the Next.js API route calls the backend endpoint, which generates the content inline (in a thread), and returns it directly. The Next.js route then stores the result in frontend SQLite.
**When to use:** Preferred for this phase -- simpler than adding job queue complexity for a user-triggered one-shot operation.
**Why:** Unlike STT which is auto-chained and takes minutes, PRD/diagram generation with Phi-4-mini takes 10-30 seconds. A loading spinner is acceptable. The job queue pattern would require polling infrastructure for a feature that only runs on explicit user action.
**Example:**
```python
# Backend endpoint -- synchronous generation in thread
@app.post("/recordings/{job_id}/generate-prd")
async def generate_prd_endpoint(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404)
    outcomes = job.get("outcomes", [])
    if not outcomes:
        raise HTTPException(status_code=400, detail="No outcomes to generate from")

    content = await asyncio.to_thread(generate_prd, job_id, app.state)
    return {"content": content, "title": f"PRD - {job.get('original_filename', 'Recording')}"}
```

```typescript
// Next.js API route -- proxy + store in SQLite
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const backendRes = await fetch(`http://localhost:8000/recordings/${id}/generate-prd`, { method: "POST" })
  const data = await backendRes.json()
  // Store in frontend SQLite documents table
  const doc = createDocument({
    title: data.title,
    type: "prd",
    content: data.content,
    sourceRecordingId: id,
  })
  return NextResponse.json(doc, { status: 201 })
}
```

### Pattern 3: Client-Side Mermaid Rendering
**What:** Dynamically import `mermaid` in a client component, call `mermaid.render()` with the diagram code, and insert the resulting SVG.
**When to use:** For rendering User Flow and ERD diagrams on document detail pages.
**Example:**
```tsx
"use client"
import { useEffect, useRef, useState } from "react"

export function MermaidDiagram({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function render() {
      const mermaid = (await import("mermaid")).default
      mermaid.initialize({ startOnLoad: false, theme: "neutral" })
      try {
        // Validate syntax first
        await mermaid.parse(code)
        const { svg } = await mermaid.render(`mermaid-${Date.now()}`, code)
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
        }
      } catch (err) {
        if (!cancelled) setError(String(err))
      }
    }
    render()
    return () => { cancelled = true }
  }, [code])

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <p className="font-medium text-destructive">Diagram rendering error</p>
        <pre className="mt-2 text-sm overflow-x-auto">{code}</pre>
      </div>
    )
  }

  return <div ref={containerRef} className="flex justify-center" />
}
```

### Pattern 4: Frontend SQLite Documents Table
**What:** New `documents` table in the frontend SQLite schema, following the same pattern as tasks/outcomes.
**Example schema:**
```sql
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('prd', 'user_flow', 'erd')),
  content TEXT NOT NULL,
  source_recording_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (source_recording_id) REFERENCES recordings(id)
);
```

### Anti-Patterns to Avoid
- **Server-side Mermaid rendering:** Do not try to render Mermaid on the server. It requires a browser DOM. Always use `"use client"` and dynamic imports.
- **Storing documents in backend storage.py:** The backend job store is for transcription jobs. Documents are a frontend concept -- store in the frontend SQLite database alongside tasks and outcomes.
- **Using response_format JSON schema for PRD generation:** PRDs are natural language prose, not structured JSON. Use plain text completion (no `response_format` parameter) for PRDs. Only use JSON schema constraint for diagram metadata if needed.
- **Generating both diagram types at once:** User selects which diagram type. Separate endpoints or a type parameter on a single endpoint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mermaid diagram rendering | Custom SVG generation from data | `mermaid` npm package `render()` API | Mermaid handles layout algorithms, arrow routing, text wrapping |
| Mermaid syntax validation | Regex-based syntax checker | `mermaid.parse()` built-in validation | Catches all syntax errors before render attempt |
| Markdown rendering for PRDs | Custom HTML generation | Simple styled `<div>` with whitespace-pre-wrap or a lightweight markdown renderer | PRD content is mostly paragraphs and lists |
| Unique render IDs for Mermaid | Manual counter | `Date.now()` or `crypto.randomUUID()` in render ID | Mermaid requires unique element IDs per render call |

**Key insight:** The LLM does the heavy lifting of generating both PRD prose and Mermaid syntax. The application layer is just prompt engineering + rendering. Keep the rendering layer thin.

## Common Pitfalls

### Pitfall 1: Mermaid SSR Crash
**What goes wrong:** Importing `mermaid` at the module level in a Next.js component causes "window is not defined" errors during server-side rendering.
**Why it happens:** Mermaid requires browser DOM APIs (window, document) that don't exist in Node.js.
**How to avoid:** Always use dynamic `import("mermaid")` inside a `useEffect` or event handler. Never import at the top of the file. The component must have `"use client"` directive.
**Warning signs:** Build errors or hydration mismatches mentioning window/document.

### Pitfall 2: LLM Generating Invalid Mermaid Syntax
**What goes wrong:** Phi-4-mini may generate Mermaid code with syntax errors (unclosed brackets, invalid node IDs with special characters, wrong arrow syntax).
**Why it happens:** Small quantized models are less reliable at generating precise DSL syntax.
**How to avoid:** (1) Include concrete Mermaid examples in the system prompt. (2) Use `mermaid.parse()` to validate before rendering. (3) Show fallback UI with raw code and a "regenerate" option on failure. (4) Keep diagrams simple -- fewer nodes means fewer syntax opportunities for error.
**Warning signs:** Blank diagram area, console errors from Mermaid parser.

### Pitfall 3: Mermaid Render ID Collision
**What goes wrong:** Calling `mermaid.render()` with the same ID twice causes rendering failures or DOM corruption.
**Why it happens:** Mermaid injects SVG elements with the given ID into the DOM. Reusing IDs causes conflicts.
**How to avoid:** Generate a unique ID per render call: `mermaid-${crypto.randomUUID()}` or use a ref-based counter.
**Warning signs:** Diagram not appearing, or previous diagram being overwritten.

### Pitfall 4: Mermaid Node Labels with Special Characters
**What goes wrong:** LLM generates node labels containing parentheses, brackets, or quotes that break Mermaid syntax.
**Why it happens:** Mermaid uses these characters as delimiters (e.g., `A[label]`, `B(label)`, `C{label}`).
**How to avoid:** Instruct the LLM in the system prompt to use only alphanumeric characters and spaces in labels, or to wrap labels in quotes. Post-process the output to escape special characters if needed.
**Warning signs:** Parse errors mentioning unexpected tokens.

### Pitfall 5: Long LLM Generation Blocking the Backend Worker
**What goes wrong:** If PRD/diagram generation goes through the job queue, it blocks STT and extraction jobs since the queue processes sequentially.
**Why it happens:** Single-worker sequential queue design.
**How to avoid:** Use synchronous endpoint approach (Pattern 2 above) -- the `asyncio.to_thread` call runs in a thread pool separate from the job queue worker. The job queue remains available for STT/extraction.
**Warning signs:** New recording uploads stuck in "pending" while document generation is running.

## Code Examples

### PRD System Prompt (Recommended)
```python
PRD_SYSTEM_PROMPT = """You are a technical writer. Generate a Professional Requirements Document (PRD) from the meeting outcomes below.

Structure the PRD with these sections:
1. **Overview** - Brief project summary based on the discussion
2. **Decisions Made** - Key decisions agreed upon
3. **Requirements** - Stated needs and constraints
4. **Action Items** - Tasks assigned with owners where known
5. **Risks & Blockers** - Impediments identified

Guidelines:
- Write in professional, clear prose
- Reference specific speakers and timestamps where relevant
- Group related items logically
- Use bullet points for lists
- Keep each section concise but complete
- Use markdown formatting (headers, bold, bullets)"""
```

### Mermaid User Flow Prompt (Recommended)
```python
USERFLOW_SYSTEM_PROMPT = """You are a diagram specialist. Generate a Mermaid flowchart diagram from the meeting outcomes below.

Rules for valid Mermaid syntax:
- Start with `flowchart TD` (top-down direction)
- Use simple alphanumeric node IDs (A, B, C or step1, step2)
- Use square brackets for labels: A[Start Process]
- Use --> for arrows with optional labels: A -->|action| B
- Use diamond braces for decisions: D{Decision?}
- Keep labels short (max 5 words)
- Do NOT use special characters in labels (no parentheses, quotes, or colons)
- Maximum 12 nodes to keep the diagram readable
- Output ONLY the Mermaid code, no explanation or markdown fences

Example:
flowchart TD
    A[User Records Meeting] --> B[Transcription]
    B --> C{Outcomes Extracted?}
    C -->|Yes| D[Review Outcomes]
    C -->|No| E[Retry]
    D --> F[Generate Documents]"""
```

### Mermaid ERD Prompt (Recommended)
```python
ERD_SYSTEM_PROMPT = """You are a diagram specialist. Generate a Mermaid Entity Relationship Diagram from the meeting requirements and entities discussed.

Rules for valid Mermaid syntax:
- Start with `erDiagram`
- Use UPPERCASE entity names with no spaces: USER, PROJECT, RECORDING
- Relationships use: ||--o{ (one to many), ||--|| (one to one), }o--o{ (many to many)
- Attributes use: string, int, date types
- Keep to essential entities only (max 6)
- Output ONLY the Mermaid code, no explanation or markdown fences

Example:
erDiagram
    USER ||--o{ RECORDING : creates
    RECORDING ||--o{ OUTCOME : contains
    OUTCOME ||--o| TASK : promotes_to
    RECORDING {
        string id
        string title
        int duration
        date created_at
    }"""
```

### Documents DB Module Pattern
```typescript
// src/lib/db/documents.ts -- follows tasks.ts pattern
import crypto from "crypto"
import { getDb } from "./index"

export interface Document {
  id: string
  title: string
  type: "prd" | "user_flow" | "erd"
  content: string
  sourceRecordingId: string
  createdAt: string
}

interface DocumentRow {
  id: string
  title: string
  type: string
  content: string
  source_recording_id: string
  created_at: string
}

function rowToDocument(row: DocumentRow): Document {
  return {
    id: row.id,
    title: row.title,
    type: row.type as Document["type"],
    content: row.content,
    sourceRecordingId: row.source_recording_id,
    createdAt: row.created_at,
  }
}

export function createDocument(data: {
  title: string
  type: Document["type"]
  content: string
  sourceRecordingId: string
}): Document {
  const db = getDb()
  const id = crypto.randomUUID()
  db.prepare(
    `INSERT INTO documents (id, title, type, content, source_recording_id)
     VALUES (?, ?, ?, ?, ?)`
  ).run(id, data.title, data.type, data.content, data.sourceRecordingId)
  return getDocument(id)!
}

export function getDocument(id: string): Document | null {
  const db = getDb()
  const row = db.prepare("SELECT * FROM documents WHERE id = ?").get(id) as DocumentRow | undefined
  return row ? rowToDocument(row) : null
}

export function listDocuments(filters?: { type?: string | null }): Document[] {
  const db = getDb()
  const conditions: string[] = []
  const params: unknown[] = []
  if (filters?.type) {
    conditions.push("type = ?")
    params.push(filters.type)
  }
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : ""
  const rows = db.prepare(
    `SELECT * FROM documents ${where} ORDER BY created_at DESC`
  ).all(...params) as DocumentRow[]
  return rows.map(rowToDocument)
}

export function countDocuments(): number {
  const db = getDb()
  const row = db.prepare("SELECT COUNT(*) as count FROM documents").get() as { count: number }
  return row.count
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| mermaid.mermaidAPI.render (callback) | mermaid.render() returns Promise with { svg } | Mermaid v10+ (2023) | Use async/await pattern, not callbacks |
| mermaid.init() for auto-rendering | mermaid.run() or manual mermaid.render() | Mermaid v10+ | Prefer explicit render() for React components |
| mermaid v9 theming | mermaid v11 theme system with `theme: "neutral"` | Mermaid v11 (2024) | Use v11 theme API |

**Deprecated/outdated:**
- `mermaidAPI.render()` with callback: Replaced by `mermaid.render()` returning a Promise
- `mermaid.init()`: Replaced by `mermaid.run()` for auto-scanning, but for React use `mermaid.render()` explicitly
- `mermaid.contentLoaded()`: Deprecated, use `mermaid.run()` instead

## Open Questions

1. **PRD markdown rendering approach**
   - What we know: PRD content is LLM-generated markdown (headers, bullets, bold). The app doesn't currently use a markdown renderer.
   - What's unclear: Whether to add a markdown rendering library or use simple CSS styling with `whitespace-pre-wrap`.
   - Recommendation: For a polished FYP demo, use simple CSS-based rendering. The LLM output can use plain text with section headers styled via CSS. If markdown rendering is needed, a lightweight `react-markdown` import could work but adds a dependency. Start with CSS-only -- if the output looks good enough, skip the dependency.

2. **Mermaid theme matching the app's indigo theme**
   - What we know: Mermaid supports `theme: "neutral"` and custom theme variables.
   - What's unclear: Whether the neutral theme will look cohesive with the app's indigo/oklch color scheme.
   - Recommendation: Start with `theme: "neutral"` which uses grays. If it clashes, pass `themeVariables` to align primary colors with indigo. This is cosmetic and can be adjusted after initial implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 4.x (frontend), pytest (backend) |
| Config file | vitest.config.ts, backend/tests/conftest.py |
| Quick run command | `npm test` |
| Full suite command | `npm test && cd backend && python -m pytest tests/` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | PRD generation from outcomes via API | integration | `npm test -- src/app/api/documents` | No -- Wave 0 |
| DOC-01 | Documents table CRUD operations | unit | `npm test -- src/lib/db/documents.test.ts` | No -- Wave 0 |
| DOC-02 | Diagram generation endpoint returns Mermaid code | integration | `cd backend && python -m pytest tests/test_document_generation.py` | No -- Wave 0 |
| DOC-03 | Mermaid.parse() validates generated syntax | unit | `npm test -- src/components/document/mermaid-diagram.test.tsx` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `npm test`
- **Per wave merge:** `npm test && cd backend && python -m pytest tests/`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `src/lib/db/documents.test.ts` -- covers DOC-01 (CRUD operations)
- [ ] `src/app/api/documents/__tests__/route.test.ts` -- covers DOC-01 (API routes)
- [ ] `backend/tests/test_document_generation.py` -- covers DOC-02 (Mermaid generation)
- [ ] Documents table added to `schema.sql` -- required before any tests run

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/extraction.py`, `backend/job_queue.py`, `backend/main.py` -- existing LLM integration patterns
- Codebase analysis: `src/lib/db/tasks.ts`, `src/app/api/tasks/route.ts` -- established CRUD patterns
- Codebase analysis: `src/hooks/use-dashboard-stats.ts`, `src/app/(dashboard)/page.tsx` -- dashboard stat card patterns
- [Mermaid.js official docs](https://mermaid.js.org/) -- API reference, render() usage
- [Mermaid npm package](https://www.npmjs.com/package/mermaid) -- v11.13.0 latest

### Secondary (MEDIUM confidence)
- [Next.js + Mermaid integration patterns](https://www.andynanopoulos.com/blog/how-to-integrate-next-react-mermaid-markdown) -- client-side dynamic import approach
- [Mermaid React rendering](https://dev.to/navdeepm20/how-i-rendered-mermaid-diagrams-in-react-and-built-a-library-for-it-c4d) -- useEffect + render() pattern

### Tertiary (LOW confidence)
- LLM prompt engineering for Mermaid syntax -- based on general LLM prompting knowledge, needs validation with actual Phi-4-mini output

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- mermaid.js is the only new dependency, well-documented; all other libraries are already in use
- Architecture: HIGH -- follows established codebase patterns exactly (tasks.ts, extraction.py, job_queue.py)
- Pitfalls: HIGH -- Mermaid SSR issues and LLM syntax errors are well-documented community problems
- Prompt engineering: MEDIUM -- prompts need testing with actual Phi-4-mini model output; may need iteration

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no fast-moving dependencies)

