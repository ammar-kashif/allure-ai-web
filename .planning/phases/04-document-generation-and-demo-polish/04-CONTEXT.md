# Phase 4: Document Generation and Demo Polish - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can generate PRD documents and Mermaid diagrams (user flow, ERD) from a recording's extracted outcomes and requirements. Generated documents are listed on a /documents page and viewable on dedicated pages. Dashboard gains a "Documents Generated" stat card. This is the stretch/polish phase — no new core pipeline capabilities.

</domain>

<decisions>
## Implementation Decisions

### PRD Generation
- Triggered from the recording detail page — "Generate PRD" button alongside existing Outcomes tab
- Auto-selects all outcomes and requirements from that recording — one-click generation, no cherry-picking
- AI-generated prose using LLM (Phi-4-mini via llama.cpp, same backend as extraction)
- LLM composes a natural language PRD from the structured outcome data
- Output rendered as styled markdown in-app — no download/export in v1
- PRD displays on a dedicated /documents/[id] page after generation

### Mermaid Diagram Generation
- Triggered from the recording detail page — "Generate Diagram" button (user picks type: User Flow or ERD)
- Two diagram types: User Flow flowchart (from action items/decisions) and ERD (from requirements/entities)
- AI-generated Mermaid syntax — LLM analyzes outcomes and generates the diagram code
- Rendered as inline SVG using Mermaid.js — no code block, just the visual diagram
- Each generated diagram saved and viewable on its own /documents/[id] page

### Documents Page & Navigation
- Sidebar "Documents" nav item activated with /documents route
- Documents list page with table: Title, Type (PRD/User Flow/ERD badge), Source Recording, Date Generated
- Type filter tabs: All / PRDs / Diagrams — consistent with Recording Hub and Task list tab patterns
- Clicking a document navigates to /documents/[id] — dedicated full-page view
- Back button returns to list

### Dashboard Integration
- Add 4th stat card: "Documents Generated" — completes the pipeline story (Recordings → Outcomes → Tasks → Documents)
- No changes to recent activity section — stays with recordings and outcomes only

### Demo Polish Scope
- Phase 4 is scoped to document generation only — no additional demo preparation, seed data, or landing pages
- Prior phases are considered polished enough for FYP demo

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

</decisions>

<specifics>
## Specific Ideas

- AI-generated PRD prose makes the demo more impressive than template fill-in — shows end-to-end AI pipeline
- Inline SVG rendering for Mermaid makes diagrams visually impactful during FYP presentation
- Documents page completes the sidebar navigation story — all 4 items (Dashboard, Recordings, Tasks, Documents) are active
- 4th stat card "Documents Generated" closes the pipeline loop on the dashboard
- One-click generation from recording detail is consistent with Phase 2's one-click promote pattern

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/components/ui/table.tsx` — Table component for documents list (same as Recording Hub and Task list)
- `src/components/ui/tabs.tsx` — Tab component for type filter (All/PRDs/Diagrams)
- `src/components/ui/badge.tsx` — Badge component for document type indicators
- `src/components/ui/button.tsx` — Button component for generate actions
- `src/components/ui/skeleton.tsx` — Skeleton for loading/generating states
- `src/components/app-sidebar.tsx` — Sidebar with Documents item at `url: "#"`, `disabled: true` — needs activation
- `src/hooks/use-dashboard-stats.ts` — Dashboard stats hook — extend with document count
- `backend/job_queue.py` — Job queue for LLM processing (same queue as STT and extraction)

### Established Patterns
- shadcn/ui + Tailwind CSS + oklch colors + indigo theme (Phase 2.1)
- Space Grotesk headings + Inter body text (Phase 2.1)
- TanStack Query for data fetching with polling
- Next.js API routes proxy all backend calls
- SQLite (better-sqlite3) for frontend metadata
- Tab bar filtering pattern (Recording Hub, Task list)
- Backend sequential job queue — one heavy model at a time
- `sonner` for toast notifications

### Integration Points
- `src/components/app-sidebar.tsx` — Activate Documents nav item (`url: "/documents"`, remove disabled)
- `src/app/(dashboard)/` — New `/documents` and `/documents/[id]` routes
- Recording detail page — Add "Generate PRD" and "Generate Diagram" buttons
- `src/lib/db/schema.sql` — New documents table
- `src/hooks/` — New `use-documents.ts` hook
- `src/hooks/use-dashboard-stats.ts` — Add document count query
- Backend — New endpoints: `POST /recordings/{id}/generate-prd`, `POST /recordings/{id}/generate-diagram`, `GET /documents/{id}`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-document-generation-and-demo-polish*
*Context gathered: 2026-03-15*
