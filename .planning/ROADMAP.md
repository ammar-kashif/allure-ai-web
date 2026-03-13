# Roadmap: Allure AI

## Overview

Allure delivers a complete Record-to-Tasks pipeline in 4 phases over ~2 weeks. Phase 1 establishes the recording and transcription foundation by integrating the Next.js frontend with the existing Python backend. Phase 2 builds the AI extraction and promotion pipeline -- the core differentiator. Phase 3 delivers task management UI (parallelizable with Phase 2). Phase 4 adds stretch document generation features and demo polish. The core demo path (Record, Transcribe, Extract, Tasks) is fully delivered by the end of Phase 3.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Recording and Transcription Pipeline** - Frontend scaffolding, audio recording, backend integration, transcript display
- [ ] **Phase 1.1: Python Backend: FastAPI + Moonshine STT** - FastAPI server, audio upload, Moonshine transcription, speaker diarization (INSERTED)
- [ ] **Phase 2: AI Extraction and Promotion** - Outcome extraction from transcripts, confidence-gated review, promotion to tasks/requirements
- [x] **Phase 2.1: UI/UX Overhaul - Modern SaaS Dashboard** - Sidebar navigation, indigo theme, typography, dashboard home, component polish (INSERTED) (completed 2026-03-13)
- [ ] **Phase 3: Task Management** - Task CRUD, list view, Kanban board (parallelizable with Phase 2)
- [ ] **Phase 4: Document Generation and Demo Polish** - PRD generation, Mermaid diagrams, demo preparation (stretch)

## Phase Details

### Phase 1: Recording and Transcription Pipeline
**Goal**: Users can record audio in the browser, see it in the Recording Hub, send it to the backend for transcription, and view the resulting timestamped, speaker-labeled transcript
**Depends on**: Nothing (first phase)
**Requirements**: REC-01, REC-02, REC-03, REC-04, REC-05, REC-06, STT-01, STT-02, STT-03, STT-04
**Success Criteria** (what must be TRUE):
  1. User can tap a global record button from any screen, record audio, and stop -- the recording appears in the Recording Hub
  2. Recordings persist across page refreshes and survive a browser crash mid-recording
  3. User can assign a recording to a project or leave it unassigned (unassigned recordings are private)
  4. After assignment, the recording is sent to the backend and processing status updates live (queued, processing, complete)
  5. Completed transcript displays with timestamps and speaker labels (Speaker 1, Speaker 2, etc.)
**Plans**: 5 plans

Plans:
- [x] 01-00-PLAN.md -- Wave 0: Test infrastructure, vitest config, test skeleton files
- [x] 01-01-PLAN.md -- Project scaffolding, audio recording pipeline with crash recovery, global FAB
- [x] 01-02-PLAN.md -- SQLite database, API routes, TanStack Query hooks
- [ ] 01-03-PLAN.md -- Recording Hub UI with table, tabs, project assignment
- [ ] 01-04-PLAN.md -- Transcript display with chat bubbles, recording detail page, end-to-end verification

### Phase 1.1: Python Backend: FastAPI + Moonshine STT (INSERTED)

**Goal**: Build the Python FastAPI backend with audio upload, Moonshine Voice transcription with speaker diarization, and transcript retrieval endpoints that the Next.js frontend proxy routes already expect at localhost:8000
**Depends on**: Phase 1
**Requirements**: BE-01, BE-02, BE-03, BE-04, BE-05, BE-06
**Success Criteria** (what must be TRUE):
  1. FastAPI server runs at localhost:8000 with CORS configured for localhost:3000
  2. POST /recordings accepts audio file upload (mp3/mp4/wav/webm/m4a), saves to disk, returns job ID
  3. Moonshine Voice processes uploaded audio and produces timestamped transcript segments
  4. Speaker diarization assigns speaker labels (Speaker 1, Speaker 2, etc.) to transcript segments
  5. GET /recordings/{id}/transcript returns full transcript with metadata, segments (start/end/text/speaker), and speaker stats
  6. GET /recordings/{id}/status returns processing status (pending/processing/completed/failed) compatible with frontend status mapping
**Plans**: 2 plans

Plans:
- [ ] 01.1-01-PLAN.md -- FastAPI server, Pydantic models, job queue, upload/status endpoints, integration tests
- [ ] 01.1-02-PLAN.md -- Moonshine STT + pyannote diarization pipeline, transcript endpoint, end-to-end verification

### Phase 2: AI Extraction and Promotion
**Goal**: Users can trigger AI extraction on a transcript and get structured outcomes (decisions, action items, requirements, blockers) with confidence scores and evidence links, then promote them into tasks and requirement records
**Depends on**: Phase 1
**Requirements**: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, EXT-06, EXT-07
**Success Criteria** (what must be TRUE):
  1. After extraction runs, outcomes appear grouped by type (decisions, action items, requirements, blockers) with confidence scores
  2. Each outcome shows an evidence link that identifies which transcript utterance(s) it came from
  3. Items below 0.80 confidence are visually distinct (flagged) from high-confidence items
  4. User can promote an action item to a task and a requirement to a requirement record -- both retain backlinks to the source transcript and audio timestamp
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md -- Backend extraction pipeline: LLM module, job queue chaining, outcome/promote endpoints
- [ ] 02-02-PLAN.md -- Frontend data layer: TypeScript types, SQLite schema, proxy routes, hooks, stores
- [ ] 02-03-PLAN.md -- Outcomes tab UI: grouped cards, confidence flagging, evidence links, promotion flow

### Phase 02.1: UI/UX Overhaul - Modern SaaS Dashboard (INSERTED)

**Goal:** Transform the existing functional UI into a polished modern SaaS dashboard with collapsible sidebar navigation, indigo color theme, Space Grotesk + Inter typography, stats-driven dashboard home, and component polish across all existing views
**Depends on:** Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Collapsible sidebar navigation with Dashboard, Recordings, Tasks (placeholder), Documents (placeholder), Settings
  2. Deep indigo primary color theme applied consistently across all components
  3. Space Grotesk headings and Inter body text throughout
  4. Dashboard home page with stat cards (Total Recordings, Outcomes Extracted, Tasks Created) and recent activity
  5. Recording Hub has text search and project dropdown filter
  6. All outcome cards, transcript bubbles, status badges, and FAB polished with indigo theme
**Plans:** 3/3 plans complete

Plans:
- [x] 02.1-01-PLAN.md -- Indigo theme, Space Grotesk/Inter fonts, sidebar layout with AppSidebar
- [x] 02.1-02-PLAN.md -- Dashboard home page with stat cards, recent activity, empty state
- [ ] 02.1-03-PLAN.md -- Recording Hub search/filter, component polish, visual verification checkpoint

### Phase 3: Task Management
**Goal**: Users can manage tasks through full CRUD operations in both list and Kanban views
**Depends on**: Phase 1 (for project context); can be built in parallel with Phase 2
**Requirements**: TASK-01, TASK-02, TASK-03, TASK-04, TASK-05
**Success Criteria** (what must be TRUE):
  1. User can create a task with title, status, priority, due date, assignee, and tags -- and can edit or delete it
  2. Tasks display in a sortable and filterable list view
  3. Tasks display in a Kanban board where dragging a card between columns updates its status
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Document Generation and Demo Polish
**Goal**: Users can generate PRD documents and Mermaid diagrams from project data (stretch goals completed if time permits)
**Depends on**: Phase 2, Phase 3
**Requirements**: DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):
  1. User can generate a PRD from approved outcomes and requirements using a template
  2. User can generate Mermaid diagrams (user flow, ERD) from project data and they render without syntax errors
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 1.1 -> 2 -> 2.1 -> 3 -> 4
Note: Phase 3 can be worked on in parallel with Phase 2 by a different team member.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Recording and Transcription Pipeline | 3/5 | In Progress |  |
| 1.1. Python Backend: FastAPI + Moonshine STT | 0/2 | Not started | - |
| 2. AI Extraction and Promotion | 2/3 | In Progress | - |
| 2.1. UI/UX Overhaul - Modern SaaS Dashboard | 3/3 | Complete   | 2026-03-13 |
| 3. Task Management | 0/2 | Not started | - |
| 4. Document Generation and Demo Polish | 0/1 | Not started | - |
