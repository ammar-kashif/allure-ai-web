---
phase: 06-speaker-management-recording-ux
plan: 01
subsystem: api, ui
tags: [fastapi, tanstack-query, inline-edit, speaker-diarization, optimistic-updates]

# Dependency graph
requires:
  - phase: 05-diarization-upgrade-audio-playback
    provides: speaker stats, diarization pipeline, transcript types
provides:
  - PATCH /recordings/{job_id}/speakers/{speaker_label} backend endpoint
  - assign_default_roles() in transcription pipeline
  - InlineEdit reusable component
  - useUpdateSpeaker mutation hook with optimistic updates
  - Next.js proxy route for speaker updates with cache invalidation
  - Extended SpeakerStat type with customLabel and role
affects: [06-02, speaker-editing-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [optimistic-mutation-with-rollback, inline-edit-pattern, proxy-cache-invalidation]

key-files:
  created:
    - src/components/transcript/inline-edit.tsx
    - src/app/api/recordings/[id]/speakers/[label]/route.ts
  modified:
    - backend/main.py
    - backend/transcription.py
    - src/types/recording.ts
    - src/hooks/use-recordings.ts
    - src/app/api/recordings/[id]/transcript/route.ts
    - src/lib/db/recordings.ts

key-decisions:
  - "InlineEdit uses local useState for editing/draft state (not Zustand)"
  - "Pencil icon always visible (not hover-to-reveal) per user preference"
  - "assign_default_roles preserves existing values via .get() for idempotency"
  - "clearCachedTranscript sets transcript_data=NULL for cache invalidation"

patterns-established:
  - "Optimistic mutation: cancel queries, snapshot, update, revert on error, invalidate on settle"
  - "Inline edit: click-to-edit with Enter/Escape/blur save, auto-focus, trim+revert on empty"

requirements-completed: [SPKR-01, SPKR-02]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 06 Plan 01: Speaker Update Infrastructure Summary

**Backend speaker update endpoint with role auto-assignment, InlineEdit component, and TanStack Query optimistic mutation hook**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T19:22:50Z
- **Completed:** 2026-03-18T19:26:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Backend PATCH endpoint for updating speaker custom_label and role with URL-decoded labels
- Transcription pipeline auto-assigns "Presenter" (top talker) and "Participant" roles
- Reusable InlineEdit component with pencil icon, click-to-edit, Enter/Escape/blur handling
- useUpdateSpeaker mutation with optimistic cache updates and error rollback
- Next.js proxy route with automatic transcript cache invalidation on speaker update

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend speaker update endpoint and role auto-assignment** - `2e1851e` (feat)
2. **Task 2: Frontend types, InlineEdit component, proxy route, and mutation hook** - `9e93b12` (feat)

## Files Created/Modified
- `backend/transcription.py` - Added assign_default_roles() function, called in pipeline
- `backend/main.py` - Added PATCH /recordings/{job_id}/speakers/{speaker_label} endpoint
- `src/types/recording.ts` - Extended SpeakerStat with customLabel and role
- `src/components/transcript/inline-edit.tsx` - Reusable inline text edit component
- `src/app/api/recordings/[id]/speakers/[label]/route.ts` - Next.js PATCH proxy route
- `src/hooks/use-recordings.ts` - Added useUpdateSpeaker mutation hook
- `src/app/api/recordings/[id]/transcript/route.ts` - Pass customLabel and role in transform
- `src/lib/db/recordings.ts` - Added clearCachedTranscript helper

## Decisions Made
- InlineEdit uses local useState (not Zustand) per research anti-pattern guidance
- Pencil icon always visible per user preference
- assign_default_roles uses .get() to preserve existing values (idempotent for migrations)
- Cache invalidation via clearCachedTranscript(id) setting transcript_data=NULL

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added clearCachedTranscript to DB layer**
- **Found during:** Task 2 (proxy route creation)
- **Issue:** Plan mentioned checking for available cache-clearing methods; neither existed
- **Fix:** Added clearCachedTranscript(id) function to src/lib/db/recordings.ts
- **Files modified:** src/lib/db/recordings.ts
- **Verification:** TypeScript compilation passes
- **Committed in:** 9e93b12 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential helper for cache invalidation. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All contracts and plumbing ready for Plan 02 to wire speaker editing into UI
- InlineEdit component ready for use in SpeakerStatsPanel and TranscriptView
- useUpdateSpeaker hook ready for UI event wiring

---
*Phase: 06-speaker-management-recording-ux*
*Completed: 2026-03-18*

