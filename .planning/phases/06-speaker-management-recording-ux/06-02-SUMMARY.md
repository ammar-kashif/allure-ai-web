---
phase: 06-speaker-management-recording-ux
plan: 02
subsystem: ui
tags: [react, inline-edit, speaker-management, transcript]

# Dependency graph
requires:
  - phase: 06-01
    provides: InlineEdit component, useUpdateSpeaker hook, SpeakerStat type extensions
provides:
  - Inline speaker name and role editing in SpeakerStatsPanel
  - Display name and role propagation to UtteranceBubble via speaker lookup map
affects: [07-document-context]

# Tech tracking
tech-stack:
  added: []
  patterns: [speaker-lookup-map-in-transcript-view]

key-files:
  created: []
  modified:
    - src/components/transcript/speaker-stats-panel.tsx
    - src/components/transcript/speaker-badge.tsx
    - src/components/transcript/utterance-bubble.tsx
    - src/components/transcript/transcript-view.tsx
    - src/app/(dashboard)/recordings/[id]/page.tsx

key-decisions:
  - "Speaker lookup map built with useMemo in TranscriptView from transcript.speakers array"
  - "Role displayed between speaker name and timestamp in utterance bubbles"
  - "Color mapping always uses original speaker label, never displayName"

patterns-established:
  - "Speaker display name resolution: build Map from transcript.speakers, pass displayName/role as props"

requirements-completed: [SPKR-01, SPKR-02]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 6 Plan 2: Speaker Inline Editing & Propagation Summary

**Inline speaker name/role editing in stats panel with display name propagation to transcript utterance bubbles via useMemo lookup map**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T19:31:08Z
- **Completed:** 2026-03-18T19:34:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- SpeakerStatsPanel wired with InlineEdit for both name and role, calling useUpdateSpeaker mutation
- SpeakerBadge accepts displayName prop while preserving original speaker label for color mapping
- UtteranceBubble displays custom speaker names and roles from speaker lookup map
- TranscriptView builds speaker Map from transcript.speakers for efficient per-utterance lookup

## Task Commits

Each task was committed atomically:

1. **Task 1: Add inline editing to SpeakerStatsPanel and update SpeakerBadge** - `f43b88f` (feat)
2. **Task 2: Propagate display names and roles to UtteranceBubble** - `b75c0ec` (feat)

## Files Created/Modified
- `src/components/transcript/speaker-stats-panel.tsx` - Added recordingId prop, InlineEdit for name/role, useUpdateSpeaker mutation
- `src/components/transcript/speaker-badge.tsx` - Added displayName prop, renders it while using original speaker for color
- `src/components/transcript/utterance-bubble.tsx` - Added displayName/role props, displays custom name and role badge
- `src/components/transcript/transcript-view.tsx` - Builds speaker lookup map with useMemo, passes displayName/role to bubbles
- `src/app/(dashboard)/recordings/[id]/page.tsx` - Passes recordingId to SpeakerStatsPanel

## Decisions Made
- Speaker lookup map built with useMemo in TranscriptView from transcript.speakers array for efficient per-utterance resolution
- Role displayed between speaker name and timestamp in utterance bubbles (not after timestamp)
- Color mapping always uses original speaker label (never displayName) to prevent color collisions on rename

## Deviations from Plan

None - plan executed exactly as written. Task 1 changes were already present in working tree from Plan 01 execution.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Speaker management UI complete: users can rename speakers and assign roles
- Changes propagate to all utterance bubbles in real-time
- Outcomes tab remains unaffected (uses original speaker labels)
- Ready for Phase 7 document context features

## Self-Check: PASSED

- f43b88f: FOUND (Task 1 commit)
- b75c0ec: FOUND (Task 2 commit)
- All 5 modified files verified present

---
*Phase: 06-speaker-management-recording-ux*
*Completed: 2026-03-18*
