# Allure — AI-Powered Project Manager

## What This Is

Allure is a local-first, AI-powered project management tool that turns meeting recordings into execution-ready project plans. Users record inside Allure, get speaker-labeled transcripts via Whisper STT, and AI extracts structured outcomes (decisions, action items, requirements, blockers) with confidence scoring. Approved outcomes promote directly into tasks, milestones, and documentation. Built as a Final Year Project (FYP) by a team of 2-3.

## Core Value

Recording a meeting and getting a reviewable, structured project plan out of it — with evidence links and confidence gating — in under 5 minutes.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Global one-tap recording with deferred project assignment
- [ ] Recording Hub with status views (Unassigned, Assigned, Processing, Needs Review)
- [ ] Built-in STT via Whisper with speaker diarization and confidence scoring
- [ ] Transcript editor with synced audio playback (click utterance → seek)
- [ ] Slides/docs upload (PPTX/PDF) with transcript-to-slide alignment
- [ ] Outcome extraction (decisions, action items, requirements, blockers) with evidence links
- [ ] Confidence-gated review: items below 0.80 require Admin approval
- [ ] Promote outcomes to tasks, requirements, risk entries with backlinks
- [ ] AI-assisted project planning: generate tasks, milestones, dependencies from outcomes
- [ ] Task and milestone management with list and Kanban views
- [ ] Task dependencies (blocks/blocked-by) and overdue flagging
- [ ] Milestone roll-up progress from linked tasks
- [ ] PRD generation from approved outcomes/requirements (template-based)
- [ ] Mermaid diagram generation (user flow, ERD) from project data
- [ ] QA agent: completeness/consistency scoring with 0.80 pass threshold
- [ ] Admin/Viewer access control (Admin: full access; Viewer: read-only on assigned projects)
- [ ] In-app notifications (task due, transcript ready, items needing review, approval completed)

### Out of Scope

- Enterprise features (SSO, complex orgs) — FYP scope
- Video conferencing / calendar scheduling — not a meeting platform
- External cloud LLM for core inference — local-first constraint
- Dashboards and advanced analytics — post-FYP
- AI chat assistant interface — post-FYP, use structured workflows instead
- Mobile app — web-first for FYP

## Context

- **Existing backend:** Python backend with STT pipeline already built (repo: github.com/ZainAbbas97/allure-ai). This project builds the Next.js frontend and integrates with that backend.
- **Team:** 2-3 members, FYP with ~2 week deadline — focus on polished core demo path over breadth.
- **Core demo path:** Record → Transcribe → Extract Outcomes → Generate Tasks. This end-to-end flow is the priority.
- **Local inference:** Whisper for STT (already in backend), llama.cpp for LLM on macOS M3. Quantized model (e.g., Llama 3.1 8B Q4_K_M or Mistral 7B).
- **Storage:** SQLite for all metadata/structured data, filesystem (`~/.allure/recordings/`) for audio files.
- **Target users for FYP demo:** Admin persona primarily, Viewer as secondary.

## Constraints

- **Timeline**: ~2 weeks to FYP submission — must prioritize core demo path ruthlessly
- **Tech stack**: Next.js frontend + existing Python (FastAPI) backend
- **Local-first**: All STT and LLM inference runs locally via Whisper and llama.cpp on M3 Mac
- **Database**: SQLite + filesystem for audio storage
- **Confidence threshold**: 0.80 default — below requires Admin review before authoritative
- **Team size**: 2-3 people splitting work

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Next.js frontend over macOS native | Faster to build in 2 weeks, team has web experience, existing Python backend is a natural fit | — Pending |
| SQLite over PostgreSQL | Local-first, zero setup, sufficient for FYP scale, no extra server process | — Pending |
| llama.cpp over Ollama | Direct Metal/GPU support on M3, Ollama wraps llama.cpp anyway, fewer layers | — Pending |
| Core demo path focus | 2-week deadline means polished end-to-end flow beats incomplete feature breadth | — Pending |
| Filesystem for audio | Audio blobs don't belong in DB, file paths in SQLite, simple and fast | — Pending |

---
*Last updated: 2026-03-11 after initialization*
