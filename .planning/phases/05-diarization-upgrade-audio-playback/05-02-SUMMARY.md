---
phase: 05-diarization-upgrade-audio-playback
plan: 02
subsystem: ui
tags: [zustand, typescript, tailwind, diarization]

# Dependency graph
requires: []
provides:
  - SpeakerStat type with 10 analytics fields
  - Extended Transcript type with speakers/duration/processingTime
  - Zustand audio-playback store (useAudioPlayback)
  - Exported speakerColors and getSpeakerIndex shared utilities
  - SpeakerBadge colored pill component
affects: [05-03, 05-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [shared-color-utilities, zustand-audio-store]

key-files:
  created:
    - src/stores/audio-playback.ts
    - src/components/transcript/speaker-badge.tsx
  modified:
    - src/types/recording.ts
    - src/components/transcript/utterance-bubble.tsx

key-decisions:
  - "Speaker color utilities exported from utterance-bubble.tsx as single source of truth"
  - "Audio playback store is state-only; HTMLAudioElement controlled imperatively from player component"

patterns-established:
  - "Shared speaker colors: import { speakerColors, getSpeakerIndex } from utterance-bubble"
  - "Audio playback store pattern: state-only Zustand store, imperative audio control in component"

requirements-completed: [SPKR-04]

# Metrics
duration: 1min
completed: 2026-03-18
---

# Phase 5 Plan 2: Types, Store & SpeakerBadge Summary

**SpeakerStat/Transcript type contracts, Zustand audio-playback store, and SpeakerBadge colored pill component with shared color palette**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-18T17:41:29Z
- **Completed:** 2026-03-18T17:42:37Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- SpeakerStat interface with 10 analytics fields for downstream speaker stats display
- Transcript type extended with optional speakers array, duration, and processingTime
- Zustand audio-playback store with full playback state (play/pause/seek/rate/scroll/reset)
- Speaker color utilities exported as single source of truth from utterance-bubble
- SpeakerBadge component renders colored pills using shared palette

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend TypeScript types and create audio playback store** - `8132b6b` (feat)
2. **Task 2: Extract speaker color utilities and create SpeakerBadge** - `3e57f0c` (feat)

## Files Created/Modified
- `src/types/recording.ts` - Added SpeakerStat interface, extended Transcript with speakers/duration/processingTime
- `src/stores/audio-playback.ts` - Zustand store for audio playback state and actions
- `src/components/transcript/utterance-bubble.tsx` - Exported speakerColors and getSpeakerIndex, added badge color variant
- `src/components/transcript/speaker-badge.tsx` - Colored badge/pill component for speaker names

## Decisions Made
- Speaker color utilities exported from utterance-bubble.tsx as single source of truth (rather than a separate utils file) to minimize refactoring
- Audio playback store is state-only; actual HTMLAudioElement will be controlled imperatively from the player component (Plan 03)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Type contracts ready for Plans 03 (audio player) and 04 (transcript panel)
- Audio playback store ready for player component to consume
- SpeakerBadge and shared color utilities ready for transcript panel

---
*Phase: 05-diarization-upgrade-audio-playback*
*Completed: 2026-03-18*

