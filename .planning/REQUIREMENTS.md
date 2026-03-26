# Requirements: Allure AI

**Defined:** 2026-03-26
**Core Value:** Recording a meeting and getting a reviewable, structured project plan with evidence links and confidence gating in under 5 minutes.

## v1.2 Requirements

Requirements for Quality of Life & Polish milestone. Each maps to roadmap phases.

### Video Pipeline

- [ ] **VID-01**: User can upload MP4 video files and have audio automatically extracted for STT processing
- [ ] **VID-02**: Recording duration metadata correctly reflects actual audio length (not 0)
- [ ] **VID-03**: Extracted audio runs through existing transcription pipeline without accuracy/speed loss

### PRD Rendering

- [ ] **PRD-01**: PRD tab renders markdown headings, bold, italics, and lists as formatted text (not raw `#` `*` characters)

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

(Additional QOL items will be added as identified)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Video playback/storage | We extract audio only — video content is discarded |
| Real-time transcription | Batch pipeline is simpler and sufficient |
| Custom markdown editor for PRDs | Read-only rendered display is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VID-01 | — | Pending |
| VID-02 | — | Pending |
| VID-03 | — | Pending |
| PRD-01 | — | Pending |

**Coverage:**
- v1.2 requirements: 4 total
- Mapped to phases: 0
- Unmapped: 4 ⚠️

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 after initial definition*
