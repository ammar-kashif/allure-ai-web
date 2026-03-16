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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 | 116 | 6 | Initial GSD workflow adoption, decimal phase insertion |

### Cumulative Quality

| Milestone | Plans | Verification | Audit Score |
|-----------|-------|-------------|-------------|
| v1.0 | 20 | 6/6 phases verified | 31/31 requirements |

### Top Lessons (Verified Across Milestones)

1. Run milestone audit before completion — catches integration gaps that per-phase verification misses
2. Test full cross-phase flows, not just individual endpoints
