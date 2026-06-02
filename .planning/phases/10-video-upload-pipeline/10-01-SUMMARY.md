---
phase: 10-video-upload-pipeline
plan: 01
subsystem: api
tags: [ffmpeg, ffprobe, video, upload, duration, nextjs, fastapi]

requires:
  - phase: none
    provides: existing audio upload pipeline
provides:
  - video file upload support (MP4, MOV)
  - audio extraction from video via FFmpeg
  - duration sync from backend to frontend DB
  - 500MB file size validation (client + server + backend)
  - no-audio-track detection
affects: []

tech-stack:
  added: []
  patterns:
    - "Three-layer file size validation: client toast, Next.js API 413, backend 413"
    - "Backend duration sync on status transition to ready"

key-files:
  created: []
  modified:
    - backend/audio_utils.py
    - backend/main.py
    - src/app/api/recordings/route.ts
    - src/lib/db/recordings.ts
    - src/app/api/recordings/[id]/status/route.ts
    - src/components/recording/upload-button.tsx

key-decisions:
  - "Three-layer file size validation for defense in depth"
  - "Duration synced from backend transcript response on ready transition"
  - "Original video file deleted after successful audio extraction"

patterns-established:
  - "Duration sync: backend librosa duration synced to frontend duration_ms on status ready"

requirements-completed: [VID-01, VID-02, VID-03]

duration: 2min
completed: 2026-03-26
---

# Phase 10 Plan 01: Video Upload Pipeline Summary

**MP4/MOV video upload with audio extraction, 500MB size limit, no-audio detection, and backend-to-frontend duration sync**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T07:25:21Z
- **Completed:** 2026-03-26T07:27:35Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Video files (MP4, MOV) accepted through existing upload button alongside audio formats
- Audio extracted from video via existing FFmpeg pipeline, original video cleaned up after extraction
- Duration metadata synced from backend to frontend DB, fixing the 0-duration bug for uploaded files
- Three-layer file size validation (client-side toast, Next.js API, Python backend) at 500MB
- No-audio-track detection via ffprobe with clear error message

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend video format support and validation** - `d14680c` (feat)
2. **Task 2: API route file handling and duration sync** - `40a6930` (feat)
3. **Task 3: Frontend upload button video support** - `850e8c5` (feat)

## Files Created/Modified
- `backend/audio_utils.py` - Added .mov to allowed extensions, added detect_no_audio_track() using ffprobe
- `backend/main.py` - 500MB size validation, no-audio detection, original file cleanup, improved error messages
- `src/app/api/recordings/route.ts` - Fixed hardcoded .webm extension, added 500MB size guard
- `src/lib/db/recordings.ts` - Added durationMs to updateRecording partial pick type
- `src/app/api/recordings/[id]/status/route.ts` - Syncs backend duration to frontend DB on ready transition
- `src/components/recording/upload-button.tsx` - Added .mov, 500MB client validation, "Upload File" label

## Decisions Made
- Three-layer file size validation for defense in depth (client, Next.js API, Python backend)
- Duration synced from backend transcript response (seconds converted to milliseconds) on status ready transition
- Original video file deleted after successful audio extraction to save disk space

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing TypeScript error in `src/app/api/recordings/__tests__/route.test.ts` (RequestInit type incompatibility) -- not caused by this plan's changes, out of scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Video upload pipeline complete, ready for end-to-end testing
- All existing audio upload functionality preserved

## Self-Check: PASSED

All 6 files verified present. All 3 task commits verified in git log.

---
*Phase: 10-video-upload-pipeline*
*Completed: 2026-03-26*

