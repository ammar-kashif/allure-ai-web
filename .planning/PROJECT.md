# Allure — AI-Powered Project Manager

## What This Is

Allure is a local-first, AI-powered project management tool that turns meeting recordings into execution-ready project plans. Users record inside Allure, get speaker-labeled transcripts via Moonshine Voice STT, and AI extracts structured outcomes (decisions, action items, requirements, blockers) with confidence scoring and evidence links. Approved outcomes promote directly into tasks and requirement records with backlinks. Generated PRDs and Mermaid diagrams round out the documentation pipeline. Built as a Final Year Project (FYP) by a team of 2-3.

## Core Value

Recording a meeting and getting a reviewable, structured project plan out of it — with evidence links and confidence gating — in under 5 minutes.

## Current State

**Shipped:** v1.0 MVP (2026-03-16)
**Codebase:** 10,333 LOC TypeScript + 2,278 LOC Python
**Tech stack:** Next.js 15, FastAPI, SQLite, TanStack Query, Mermaid, shadcn/ui

**What's working:**
- Full Record → Transcribe → Extract → Tasks pipeline
- Modern SaaS dashboard with sidebar nav, indigo theme, stat cards
- Task management with CRUD, list view, drag-and-drop Kanban
- Document generation (PRD + Mermaid user flow/ERD diagrams)
- Confidence-gated outcome review with evidence cross-navigation

## Requirements

### Validated

- ✓ REC-01: Global one-tap recording — v1.0
- ✓ REC-02: Browser audio capture via Web Audio API — v1.0
- ✓ REC-03: Recording auto-save with crash recovery — v1.0
- ✓ REC-04: Recording Hub with status views — v1.0
- ✓ REC-05: Project assignment for recordings — v1.0
- ✓ REC-06: Unassigned recordings are private — v1.0
- ✓ STT-01: Backend STT processing — v1.0
- ✓ STT-02: Timestamped transcript utterances — v1.0
- ✓ STT-03: Speaker diarization labels — v1.0
- ✓ STT-04: Real-time processing status updates — v1.0
- ✓ BE-01: FastAPI server with CORS and health check — v1.0
- ✓ BE-02: Audio file upload with validation — v1.0
- ✓ BE-03: Moonshine Voice STT integration — v1.0
- ✓ BE-04: Speaker diarization with SpeechBrain — v1.0
- ✓ BE-05: Transcript retrieval endpoint — v1.0
- ✓ BE-06: Processing status endpoint — v1.0
- ✓ EXT-01: AI extraction of structured outcomes — v1.0
- ✓ EXT-02: Outcomes with title, detail, confidence, evidence — v1.0
- ✓ EXT-03: Outcomes grouped by type with confidence indicators — v1.0
- ✓ EXT-04: Low-confidence items visually flagged — v1.0
- ✓ EXT-05: Promote action items to tasks with backlinks — v1.0
- ✓ EXT-06: Promote requirements to records with backlinks — v1.0
- ✓ EXT-07: Promoted items retain evidence links — v1.0
- ✓ TASK-01: Task CRUD — v1.0
- ✓ TASK-02: Tasks with title, status, priority, due date, assignee, tags — v1.0
- ✓ TASK-03: Sortable/filterable task list view — v1.0
- ✓ TASK-04: Drag-and-drop Kanban board — v1.0
- ✓ TASK-05: Kanban drag updates task status — v1.0
- ✓ DOC-01: PRD generation from outcomes — v1.0
- ✓ DOC-02: Mermaid diagram generation (user flow, ERD) — v1.0
- ✓ DOC-03: Mermaid renders without syntax errors — v1.0

### Active

#### v1.1 — Meeting Intelligence & Document Context
- [ ] Audio playback synced with transcript (click-to-seek, active line highlight)
- [ ] Editable speaker labels and speaker roles in transcription tab
- [ ] Per-speaker statistics (time, words, WPM, turns, avg turn, pauses, avg pause)
- [ ] Meeting-level statistics (duration, processing time, speaker count, attached docs)
- [ ] Post-recording popup (name, project, doc upload) with background processing
- [ ] Document attachments on recordings, used as context for PRD/Mermaid generation
- [ ] AgglomerativeClustering for speaker diarization (replace current approach)
- [ ] Smarter document generation — diagrams model the product discussed, not meeting flow
- [ ] Improved prompts for PRD and Mermaid quality

### Out of Scope

- Enterprise features (SSO, complex orgs) — FYP scope
- Video conferencing / calendar scheduling — not a meeting platform
- External cloud LLM for core inference — local-first constraint
- Mobile app — web-first for FYP
- Real-time collaborative editing — complexity too high for FYP
- AI chat assistant interface — use structured workflows instead

## Context

- **Team:** 2-3 members, FYP project
- **Core demo path:** Record → Transcribe → Extract Outcomes → Tasks/Documents
- **Local inference:** Moonshine Voice for STT, llama.cpp for LLM on macOS M3
- **Storage:** SQLite for all metadata, filesystem for audio files

## Constraints

- **Tech stack**: Next.js 15 frontend + Python FastAPI backend
- **Local-first**: All STT and LLM inference runs locally
- **Database**: SQLite + filesystem for audio storage
- **Confidence threshold**: 0.80 — below requires review

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Next.js frontend over macOS native | Faster to build, team has web experience | ✓ Good |
| SQLite over PostgreSQL | Local-first, zero setup, sufficient for FYP scale | ✓ Good |
| llama.cpp over Ollama | Direct Metal/GPU support on M3 | ✓ Good |
| Core demo path focus | 2-week deadline, polished E2E flow beats incomplete breadth | ✓ Good |
| Filesystem for audio | Audio blobs don't belong in DB, simple and fast | ✓ Good |
| SpeechBrain over pyannote for diarization | CPU-only, no gated model tokens required | ✓ Good |
| Moonshine Voice over Whisper | Faster on M-series, purpose-built for STT | ✓ Good |
| Frontend SQLite for metadata | Outcomes/tasks/documents stored frontend-side for offline resilience | ✓ Good |
| Synchronous LLM generation for documents | Avoids blocking STT worker, simpler than job queue for one-shot ops | ✓ Good |
| Zustand for cross-component state | Evidence navigation needs tab switch + scroll coordination | ✓ Good |

---
## Current Milestone: v1.1 Meeting Intelligence & Document Context

**Goal:** Enrich recording detail with synced playback, speaker analytics, document attachments as generation context, and smarter product-focused diagram output.

**Target features:**
- Synced audio playback with transcript navigation
- Speaker management (editable labels/roles) and per-speaker/meeting statistics
- Post-recording popup with background processing and doc upload
- Document attachments as context for PRD/Mermaid generation
- AgglomerativeClustering for diarization accuracy
- Product-focused diagram generation with improved prompts

---
*Last updated: 2026-03-18 after v1.1 milestone start*
