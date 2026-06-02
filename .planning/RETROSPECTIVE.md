# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-16
**Phases:** 6 | **Plans:** 20 | **Commits:** 116

### What Was Built
- Audio recording with crash recovery and global FAB, auto-uploading to FastAPI backend
- Moonshine Voice STT with SpeechBrain speaker diarization (CPU-only, no gated models)
- AI extraction pipeline producing structured outcomes with confidence gating and evidence links
- Modern SaaS dashboard with indigo theme, collapsible sidebar, Space Grotesk/Inter typography
- Task management with CRUD, sortable list, and drag-and-drop Kanban board
- Document generation (PRD + Mermaid user flow/ERD) with inline rendering

### What Worked
- Pipeline-derived phase ordering (Record -> Transcribe -> Extract -> Tasks) kept dependencies clean
- Proxy-and-store pattern: Next.js API calls backend, stores result in frontend SQLite — consistent across outcomes, tasks, documents
- Wave 0 test stubs before implementation gave structure to each phase
- Decimal phase insertion (1.1, 2.1) for urgent work without renumbering

### What Was Inefficient
- Phase 1 plans 01-03 and 01-04 were executed outside GSD workflow — lost traceability
- Dashboard stats initially counted promoted outcomes instead of actual tasks — caught in milestone audit
- Promote route shipped with hardcoded empty title/detail — integration gap discovered at audit time
- Phase 4 never got a VERIFICATION.md during execution — had to backfill

### Patterns Established
- Frontend SQLite as metadata owner (recordings, outcomes, tasks, documents) with backend as processing engine
- Evidence cross-navigation via zustand store (tab switch + scroll + highlight with 3s auto-clear)
- globalThis DB singleton pattern to survive Next.js HMR without connection leaks
- Mermaid.parse() validation before render with error fallback

### Key Lessons
1. Always run milestone audit before marking complete — it caught 3 real integration bugs
2. Proxy routes should pass through all relevant data (not hardcode empty strings) — test the full promote-and-view flow, not just the promote call
3. Dashboard stats should query authoritative source (tasks table) not proxy metrics (promoted outcome count)
4. VERIFICATION.md should be created during phase execution, not backfilled

### Cost Observations
- Model mix: primarily Opus for planning/execution, Sonnet for exploration
- 5 days wall clock, ~116 commits
- Notable: average plan execution was ~8 minutes — fast iteration with atomic commits

---

## Milestone: v1.1 — Meeting Intelligence & Document Context

**Shipped:** 2026-03-20
**Phases:** 5 | **Plans:** 13 | **Commits:** 83

### What Was Built
- AgglomerativeClustering diarization with auto speaker count, replacing MeanShift
- Audio playback with transcript-synced highlighting, click-to-seek, auto-scroll with manual override
- Speaker management: editable labels and roles with optimistic updates across transcript
- Document attachments: PDF/DOCX/TXT upload, automatic text extraction, 10MB limit
- Context-aware PRD/Mermaid generation injecting attached document text
- Post-recording dialog with background transcription and document upload

### What Worked
- Phase 9 (integration hardening) as explicit gap-closure phase — audit findings mapped directly to plan tasks
- Zustand store pattern (audio-playback, evidence-highlight, recording-store) scaled cleanly for cross-component coordination
- Coarse phase granularity (4 feature phases + 1 hardening) kept milestone focused and fast
- Research-before-plan pattern consistently surfaced design decisions early (e.g., portal vs sticky player, InlineEdit anti-patterns)
- Imperative audio element control via useRef avoided React re-render loops with HTMLAudioElement

### What Was Inefficient
- Phase 9 plans still unchecked in ROADMAP.md at audit time — verification fixed the real work but plan checkboxes lagged
- SUMMARY frontmatter `requirements_completed` missing for PLAY-02 in Plan 05-04 — caused false "partial" in 3-source cross-reference
- Nyquist validation files created for all phases but none progressed past draft — overhead without value
- No one-liner field in SUMMARY frontmatter made accomplishment extraction fail at milestone completion

### Patterns Established
- Portal-based audio player (`#player-portal` in layout.tsx) for positioning within SidebarInset
- seekGeneration counter pattern for imperative audio seeks without effect dependency on currentTime
- Speaker color mapping always uses original label (not displayName) to prevent color collisions on rename
- Save-then-forward pattern for document uploads: decouple local save from async backend forwarding
- Retry loop for race conditions (backendId resolution) over complex queue infrastructure

### Key Lessons
1. Integration hardening as an explicit phase works well — schedule it after feature phases, not as ad-hoc fixes
2. SUMMARY frontmatter `requirements_completed` must be kept accurate during execution — it's a primary source for audit cross-reference
3. Nyquist validation should only be enabled when the team commits to completing it — draft-only VALIDATION.md files add noise
4. Race conditions between async operations (upload vs transcription) need explicit handling — "it usually works" is not sufficient
5. Product-focused prompt engineering (anti-pattern guards like "Do NOT diagram the meeting") is more effective than positive-only instructions

### Cost Observations
- Model mix: Opus for planning/execution, Sonnet for exploration/verification/integration-check
- 4 days wall clock, 83 commits
- Notable: average plan execution ~3 minutes (faster than v1.0's ~8 minutes) — coarse granularity helped

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 | 116 | 6 | Initial GSD workflow adoption, decimal phase insertion |
| v1.1 | 83 | 5 | Coarse granularity, explicit hardening phase, research-before-plan |

### Cumulative Quality

| Milestone | Plans | Verification | Audit Score |
|-----------|-------|-------------|-------------|
| v1.0 | 20 | 6/6 phases verified | 31/31 requirements |
| v1.1 | 13 | 5/5 phases verified | 22/22 requirements |

### Top Lessons (Verified Across Milestones)

1. Run milestone audit before completion — catches integration gaps that per-phase verification misses (v1.0: 3 bugs, v1.1: 3 integration findings)
2. Test full cross-phase flows, not just individual endpoints (v1.0: promote route, v1.1: document forwarding race)
3. Keep SUMMARY frontmatter accurate during execution — it's a primary data source for automated audits

