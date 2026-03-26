# Roadmap: Allure AI

## Milestones

- **v1.0 MVP** — 6 phases, 20 plans (shipped 2026-03-16) | [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Meeting Intelligence & Document Context** — 5 phases, 13 plans (shipped 2026-03-20) | [archive](milestones/v1.1-ROADMAP.md)
- **v1.2 Quality of Life & Polish** — 2 phases (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-16</summary>

- [x] Phase 1: Recording and Transcription Pipeline (5/5 plans) — completed 2026-03-12
- [x] Phase 1.1: Python Backend: FastAPI + Moonshine STT (2/2 plans) — completed 2026-03-12
- [x] Phase 2: AI Extraction and Promotion (4/4 plans) — completed 2026-03-15
- [x] Phase 2.1: UI/UX Overhaul - Modern SaaS Dashboard (3/3 plans) — completed 2026-03-13
- [x] Phase 3: Task Management (3/3 plans) — completed 2026-03-13
- [x] Phase 4: Document Generation and Demo Polish (3/3 plans) — completed 2026-03-15

</details>

<details>
<summary>v1.1 Meeting Intelligence & Document Context (Phases 5-9) — SHIPPED 2026-03-20</summary>

- [x] Phase 5: Diarization Upgrade & Audio Playback (4/4 plans) — completed 2026-03-18
- [x] Phase 6: Speaker Management & Recording UX (3/3 plans) — completed 2026-03-18
- [x] Phase 7: Document Attachments (2/2 plans) — completed 2026-03-19
- [x] Phase 8: Context-Aware Generation (2/2 plans) — completed 2026-03-20
- [x] Phase 9: Integration Hardening & Tech Debt (2/2 plans) — completed 2026-03-20

</details>

### v1.2 Quality of Life & Polish (In Progress)

- [ ] **Phase 10: Video Upload Pipeline** - Accept MP4 uploads, extract audio, and produce correct duration metadata
- [ ] **Phase 11: PRD Markdown Rendering** - Render PRD content as formatted text instead of raw markdown syntax

## Phase Details

### Phase 10: Video Upload Pipeline
**Goal**: Users can upload MP4 video files and get transcripts just like audio uploads
**Depends on**: Nothing (builds on existing recording/transcription pipeline)
**Requirements**: VID-01, VID-02, VID-03
**Success Criteria** (what must be TRUE):
  1. User can select and upload an MP4 file through the same upload flow used for audio
  2. Uploaded video has its audio extracted and transcribed without manual intervention
  3. Recording detail page shows correct duration (actual audio length, not 0 or placeholder)
  4. Transcript quality and processing speed for video-extracted audio matches direct audio uploads
**Plans**: TBD

### Phase 11: PRD Markdown Rendering
**Goal**: Users see formatted, readable PRD documents instead of raw markdown syntax
**Depends on**: Nothing (independent of Phase 10)
**Requirements**: PRD-01
**Success Criteria** (what must be TRUE):
  1. PRD tab displays headings, bold, italics, and lists as properly formatted text
  2. Raw markdown characters (#, *, -, etc.) do not appear in the rendered PRD view
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 10 → 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Recording and Transcription Pipeline | v1.0 | 5/5 | Complete | 2026-03-12 |
| 1.1. Python Backend: FastAPI + Moonshine STT | v1.0 | 2/2 | Complete | 2026-03-12 |
| 2. AI Extraction and Promotion | v1.0 | 4/4 | Complete | 2026-03-15 |
| 2.1. UI/UX Overhaul - Modern SaaS Dashboard | v1.0 | 3/3 | Complete | 2026-03-13 |
| 3. Task Management | v1.0 | 3/3 | Complete | 2026-03-13 |
| 4. Document Generation and Demo Polish | v1.0 | 3/3 | Complete | 2026-03-15 |
| 5. Diarization & Audio Playback | v1.1 | 4/4 | Complete | 2026-03-18 |
| 6. Speaker Management & Recording UX | v1.1 | 3/3 | Complete | 2026-03-18 |
| 7. Document Attachments | v1.1 | 2/2 | Complete | 2026-03-19 |
| 8. Context-Aware Generation | v1.1 | 2/2 | Complete | 2026-03-20 |
| 9. Integration Hardening & Tech Debt | v1.1 | 2/2 | Complete | 2026-03-20 |
| 10. Video Upload Pipeline | v1.2 | 0/? | Not started | - |
| 11. PRD Markdown Rendering | v1.2 | 0/? | Not started | - |
