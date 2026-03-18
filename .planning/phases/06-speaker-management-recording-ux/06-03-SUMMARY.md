---
phase: 06-speaker-management-recording-ux
plan: 03
subsystem: ui
tags: [zustand, dialog, drag-drop, file-upload, recording-ux]

requires:
  - phase: 05-diarization-upgrade-audio-playback
    provides: Recording store, audio recorder hook, upload mutation
provides:
  - PostRecordingDialog component with metadata entry flow
  - FileDropZone drag-and-drop component
  - Extended recording store with dialog state
  - Documents upload API route
affects: [07-document-context, recording-hub]

tech-stack:
  added: []
  patterns: [zustand-partialize-ephemeral-state, controlled-dialog-no-dismiss]

key-files:
  created:
    - src/components/recording/post-recording-dialog.tsx
    - src/components/recording/file-drop-zone.tsx
    - src/app/api/recordings/[id]/documents/route.ts
  modified:
    - src/stores/recording-store.ts
    - src/components/recording/recording-fab.tsx

key-decisions:
  - "Used disablePointerDismissal + onKeyDown escape prevention for non-dismissible dialog"
  - "Documents saved to disk via simple API route -- Phase 7 will add DB layer and text extraction"
  - "Post-recording dialog state excluded from Zustand persistence via partialize"

patterns-established:
  - "Zustand partialize: ephemeral UI state (dialog open, pending data) excluded from persistence"
  - "Parallel upload + dialog: background mutation fires before UI dialog opens"

requirements-completed: [RUX-01, RUX-02, RUX-03]

duration: 4min
completed: 2026-03-18
---

# Phase 06 Plan 03: Post-Recording Dialog Summary

**Post-recording dialog with name/project/document fields, immediate background upload, and live transcription status polling**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-18T19:23:07Z
- **Completed:** 2026-03-18T19:27:07Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- PostRecordingDialog opens immediately after recording stops with pre-filled name, project dropdown, file drop zone, and transcription status
- Recording upload starts immediately in background before dialog opens -- user edits metadata while transcription runs
- FileDropZone supports drag-and-drop and click-to-browse for PDF/DOCX/DOC/TXT files with file list and remove buttons
- Dialog cannot be dismissed by backdrop click or escape -- only Save or Skip buttons close it
- Documents API route saves uploaded files to disk for minimal Phase 6 scope

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend recording store and create PostRecordingDialog with FileDropZone** - `13e846d` (feat)
2. **Task 2: Rewire RecordingFAB to open dialog and upload in parallel** - `54272c3` (feat)

## Files Created/Modified
- `src/stores/recording-store.ts` - Extended with showPostRecordingDialog, pendingRecording, and partialize for persistence
- `src/components/recording/post-recording-dialog.tsx` - Post-recording metadata dialog with name, project, files, and status
- `src/components/recording/file-drop-zone.tsx` - Drag-and-drop file upload zone with file list management
- `src/components/recording/recording-fab.tsx` - Rewired to upload immediately and open dialog on stop
- `src/app/api/recordings/[id]/documents/route.ts` - POST endpoint for saving reference documents to disk

## Decisions Made
- Used base-ui `disablePointerDismissal` prop + Escape key prevention for non-dismissible dialog behavior
- Document uploads saved to `public/recordings/{id}/docs/` as simple disk storage -- Phase 7 will formalize with DB records and text extraction
- Post-recording dialog state (showPostRecordingDialog, pendingRecording) excluded from Zustand persistence using partialize to keep ephemeral state clean

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Post-recording dialog flow complete -- users can name recordings, assign projects, and attach documents immediately after recording
- Document storage is minimal (disk-only) -- Phase 7 should add DB layer, text extraction, and document management UI
- Transcription status polling works via existing useRecordingStatus hook

---
*Phase: 06-speaker-management-recording-ux*
*Completed: 2026-03-18*
