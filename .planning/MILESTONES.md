# Milestones

## v1.1 Meeting Intelligence & Document Context (Shipped: 2026-03-20)

**Delivered:** Enriched recording detail with synced audio playback, speaker analytics, document attachments as generation context, and product-focused diagram output.

**Phases completed:** 5-9 (13 plans total)
**Timeline:** 4 days (2026-03-16 → 2026-03-20)

**Key accomplishments:**
1. AgglomerativeClustering diarization with auto speaker count detection, replacing MeanShift
2. Audio playback with transcript-synced highlighting, click-to-seek, and speed control
3. Speaker management: editable labels/roles with optimistic updates propagating across transcript
4. Document attachments: PDF/DOCX/TXT upload with automatic text extraction and storage
5. Context-aware generation: product-focused PRD/Mermaid with document context injection
6. Post-recording dialog with background processing and document upload

**Stats:**
- 122 files modified
- +14,251 / -1,541 lines changed
- 5 phases, 13 plans
- 83 commits over 4 days

**Git range:** `3c84635` → `78b24b0`

**Phases:**
- Phase 5: Diarization Upgrade & Audio Playback (4 plans)
- Phase 6: Speaker Management & Recording UX (3 plans)
- Phase 7: Document Attachments (2 plans)
- Phase 8: Context-Aware Generation (2 plans)
- Phase 9: Integration Hardening & Tech Debt (2 plans)

**Known tech debt:**
- Pre-existing TS type error in `src/app/api/recordings/__tests__/route.test.ts`
- AgglomerativeClustering distance_threshold=0.7 needs empirical tuning
- Nyquist validation incomplete across all 5 phases (draft VALIDATION.md only)

**Archives:** `.planning/milestones/v1.1-ROADMAP.md`, `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## v1.0 MVP (Shipped: 2026-03-16)

**Phases completed:** 6 phases, 20 plans
**Timeline:** 5 days (2026-03-11 → 2026-03-16)
**Codebase:** 10,333 LOC TypeScript + 2,278 LOC Python across 217 files

**Key accomplishments:**
1. Audio recording with crash recovery, global FAB, and auto-upload to backend
2. FastAPI backend with Moonshine Voice STT and SpeechBrain speaker diarization
3. AI extraction pipeline producing structured outcomes (decisions, action items, requirements, blockers) with confidence gating and evidence links
4. Modern SaaS dashboard with indigo theme, collapsible sidebar, Space Grotesk/Inter typography
5. Full task management with CRUD, list view, Kanban board with drag-and-drop
6. Document generation (PRD + Mermaid diagrams) with inline rendering on recording detail

**Phases:**
- Phase 1: Recording and Transcription Pipeline (5 plans)
- Phase 1.1: Python Backend — FastAPI + Moonshine STT (2 plans)
- Phase 2: AI Extraction and Promotion (4 plans)
- Phase 2.1: UI/UX Overhaul — Modern SaaS Dashboard (3 plans)
- Phase 3: Task Management (3 plans)
- Phase 4: Document Generation and Demo Polish (3 plans)

**Archives:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`

---
