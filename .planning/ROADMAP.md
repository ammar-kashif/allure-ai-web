# Roadmap: Allure AI

## Milestones

- **v1.0 MVP** — 6 phases, 20 plans (shipped 2026-03-16) | [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Meeting Intelligence & Document Context** — Phases 5-9 (in progress)

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

### v1.1 Meeting Intelligence & Document Context

- [x] **Phase 5: Diarization Upgrade & Audio Playback** - AgglomerativeClustering swap, synced audio playback with transcript highlight, speaker/meeting statistics (completed 2026-03-18)
- [x] **Phase 6: Speaker Management & Recording UX** - Editable speaker labels/roles, post-recording popup with background processing (completed 2026-03-18)
- [x] **Phase 7: Document Attachments** - Upload, parse, store, and display documents attached to recordings (completed 2026-03-19)
- [x] **Phase 8: Context-Aware Generation** - Document context injection and product-focused diagram prompts (completed 2026-03-20)
- [ ] **Phase 9: Integration Hardening & Tech Debt Cleanup** - Fix SpeakerStats model fragility, backendId race condition, and documentation gaps

## Phase Details

### Phase 5: Diarization Upgrade & Audio Playback
**Goal**: Users can play back meeting audio synced to the transcript with active line highlighting, and see enriched speaker and meeting statistics powered by improved diarization
**Depends on**: Phase 4 (v1.0 complete)
**Requirements**: DIAR-01, DIAR-02, PLAY-01, PLAY-02, PLAY-03, SPKR-03, SPKR-04, MEET-01, MEET-02, MEET-03
**Success Criteria** (what must be TRUE):
  1. User can play, pause, and change speed (0.5x/1x/1.5x/2x) of meeting audio from the recording detail page
  2. The current utterance is visually highlighted in the transcript during audio playback, updating smoothly without lag
  3. User can see per-speaker statistics (talk time, word count, WPM, turns, avg turn duration, pauses, avg pause duration) on the recording detail page
  4. User can see meeting-level statistics (duration, processing time, speaker count) on the recording detail page
  5. Speakers are color-coded in the transcript view and diarization uses AgglomerativeClustering with auto-detected speaker count
**Plans:** 3/4 plans executed

Plans:
- [ ] 05-01-PLAN.md — Backend: diarization upgrade, extended stats, processing time, WAV audio endpoint
- [ ] 05-02-PLAN.md — Frontend contracts: types, Zustand store, speaker color utilities, SpeakerBadge
- [ ] 05-03-PLAN.md — Audio player bar, meeting stat cards, speaker stats panel, page wiring
- [ ] 05-04-PLAN.md — Transcript-audio sync: highlight, auto-scroll, click-to-seek, final verification

### Phase 6: Speaker Management & Recording UX
**Goal**: Users can rename speakers, assign roles, and complete a guided post-recording flow that names the recording, assigns a project, and optionally attaches documents -- all while transcription proceeds in the background
**Depends on**: Phase 5
**Requirements**: SPKR-01, SPKR-02, RUX-01, RUX-02, RUX-03
**Success Criteria** (what must be TRUE):
  1. User can rename any speaker label (e.g., "Speaker 1" to "Alice") and the change reflects throughout the transcript
  2. User can assign a role to each speaker (e.g., "Product Manager") visible alongside their name
  3. After stopping a recording, a popup appears where user can name the recording and assign it to a project
  4. User can upload reference documents from the post-recording popup
  5. Transcription and diarization proceed in the background while the popup is open -- user does not wait
**Plans:** 3/3 plans complete

Plans:
- [ ] 06-01-PLAN.md — Backend speaker update endpoint, role auto-assignment, frontend types, InlineEdit component, mutation hook
- [ ] 06-02-PLAN.md — Wire speaker editing into SpeakerStatsPanel and propagate to UtteranceBubble
- [ ] 06-03-PLAN.md — Post-recording dialog with background processing, file upload, project assignment

### Phase 7: Document Attachments
**Goal**: Users can upload PDF/DOCX documents to recordings, with text automatically extracted and stored for downstream generation, and documents listed on the recording detail page
**Depends on**: Phase 6
**Requirements**: DOC-01, DOC-02, DOC-03, MEET-04
**Success Criteria** (what must be TRUE):
  1. User can upload PDF and DOCX documents to a recording from the recording detail page
  2. Uploaded document text is automatically extracted and stored without user intervention
  3. Attached documents are listed on the recording detail page with filename and type
  4. The meeting statistics card shows the count of attached documents
**Plans:** 2/2 plans complete

Plans:
- [x] 07-01-PLAN.md — Backend: text extraction module, attachments storage CRUD, FastAPI endpoints, n_ctx bump
- [x] 07-02-PLAN.md — Frontend: API routes, hooks, AttachedDocumentsCard, MeetingStatCards update, page wiring

### Phase 8: Context-Aware Generation
**Goal**: PRD and Mermaid generation uses attached document text as context and produces product-focused diagrams that model the system discussed, not the meeting flow
**Depends on**: Phase 7
**Requirements**: GEN-01, GEN-02, GEN-03
**Success Criteria** (what must be TRUE):
  1. When documents are attached, PRD generation incorporates their content as context, producing output grounded in the attached specs
  2. Mermaid diagrams model the product/system discussed in the meeting, not the meeting discussion flow itself
  3. PRD and Mermaid output quality is noticeably improved -- fewer syntax errors, more coherent structure, product-appropriate terminology
**Plans:** 2/2 plans complete

Plans:
- [x] 08-01-PLAN.md — Prompt overhaul, context injection plumbing, storage query, tests
- [x] 08-02-PLAN.md — Endpoint wiring, integration tests, human verification of output quality

### Phase 9: Integration Hardening & Tech Debt Cleanup
**Goal**: Harden integration points identified by milestone audit — fix SpeakerStats model fragility, resolve document forwarding race condition, and clean up documentation gaps
**Depends on**: Phase 8
**Requirements**: SPKR-01, SPKR-02, RUX-02, DOC-02, GEN-02
**Gap Closure:** Closes INT-01, INT-02, FLOW-01 from v1.1 audit
**Success Criteria** (what must be TRUE):
  1. SpeakerStats Pydantic model includes custom_label and role fields — adding response_model validation would not drop data
  2. Documents uploaded from the post-recording dialog are forwarded for text extraction even when backendId is not yet available
  3. All REQUIREMENTS.md checkboxes match audit findings (PLAY-02 marked complete)
  4. All completed phase plan checkboxes marked in ROADMAP.md
  5. No function-level imports in document_generation.py
**Plans:** 0/0 plans

Plans:
_(none yet — run `/gsd:plan-phase 9`)_

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8 -> 9

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
| 9. Integration Hardening & Tech Debt | v1.1 | 0/0 | Pending | - |
