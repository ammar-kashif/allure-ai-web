---
phase: 07-document-attachments
plan: 02
subsystem: ui
tags: [tanstack-query, next-api-routes, attachments, file-upload, alert-dialog]

# Dependency graph
requires:
  - phase: 07-document-attachments
    plan: 01
    provides: "Python backend attachment upload/list/delete endpoints and text extraction"
provides:
  - "Next.js proxy API routes for attachment CRUD (GET, POST, DELETE)"
  - "useAttachments, useUploadAttachment, useDeleteAttachment TanStack Query hooks"
  - "AttachedDocumentsCard component with upload, delete confirmation, extraction error display"
  - "MeetingStatCards 4th card for document count with Paperclip icon"
  - "FileDropZone updated: no .doc, 10MB limit with toast feedback"
  - "Post-recording dialog uploads trigger backend text extraction"
affects: [08-context-aware-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [attachment-proxy-pattern, file-upload-mutation-pattern]

key-files:
  created:
    - src/app/api/recordings/[id]/attachments/route.ts
    - src/app/api/recordings/[id]/attachments/[attachmentId]/route.ts
    - src/hooks/use-attachments.ts
    - src/components/recording/attached-documents-card.tsx
    - src/components/recording/__tests__/meeting-stat-cards.test.tsx
  modified:
    - src/app/api/recordings/[id]/documents/route.ts
    - src/components/recording/file-drop-zone.tsx
    - src/components/recording/meeting-stat-cards.tsx
    - src/app/(dashboard)/recordings/[id]/page.tsx

key-decisions:
  - "Attachment proxy routes use getRecording(id).backendId pattern consistent with all other API routes"
  - "DELETE route best-effort fetches metadata for local file cleanup before deleting from backend"
  - "AttachedDocumentsCard uses controlled AlertDialog state (open/onOpenChange) instead of trigger-based pattern"

patterns-established:
  - "Attachment proxy pattern: Next.js routes forward FormData multipart uploads to Python backend"
  - "File upload mutation pattern: useMutation with FormData, query invalidation on success, sonner toast on error"

requirements-completed: [DOC-01, DOC-03, MEET-04]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 7 Plan 02: Frontend Document Attachments Summary

**Next.js attachment proxy routes, TanStack Query hooks, AttachedDocumentsCard with upload/delete, 4th stat card for doc count, and FileDropZone 10MB/.doc cleanup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T20:51:07Z
- **Completed:** 2026-03-18T20:54:48Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Next.js proxy API routes for attachment GET/POST/DELETE forwarding to Python backend with backendId resolution
- TanStack Query hooks (useAttachments, useUploadAttachment, useDeleteAttachment) with query invalidation and toast notifications
- AttachedDocumentsCard with file upload button, attachment list, delete confirmation AlertDialog, and extraction error tooltips
- MeetingStatCards extended with 4th "Documents" card (Paperclip icon) conditionally rendered when docCount provided
- FileDropZone cleaned up: removed .doc acceptance, added 10MB size limit with sonner toast feedback
- Post-recording dialog document uploads now also POST to Python backend for text extraction
- 4 passing unit tests for MeetingStatCards docCount behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Next.js API routes and TanStack Query hooks** - `2e5a8e0` (feat)
2. **Task 2: AttachedDocumentsCard, MeetingStatCards update, FileDropZone cleanup, and page wiring** - `33adb4e` (feat)

## Files Created/Modified
- `src/app/api/recordings/[id]/attachments/route.ts` - GET/POST proxy to Python backend attachments
- `src/app/api/recordings/[id]/attachments/[attachmentId]/route.ts` - DELETE proxy with local file cleanup
- `src/hooks/use-attachments.ts` - Attachment interface, useAttachments query, upload/delete mutations
- `src/components/recording/attached-documents-card.tsx` - Card with upload, list, delete confirmation, error tooltip
- `src/components/recording/__tests__/meeting-stat-cards.test.tsx` - 4 tests for docCount rendering
- `src/app/api/recordings/[id]/documents/route.ts` - Extended to POST files to backend for extraction
- `src/components/recording/file-drop-zone.tsx` - Removed .doc, added 10MB limit with toast
- `src/components/recording/meeting-stat-cards.tsx` - Added Paperclip icon 4th stat card for documents
- `src/app/(dashboard)/recordings/[id]/page.tsx` - Wired useAttachments, AttachedDocumentsCard in Info tab, docCount to stat cards

## Decisions Made
- Attachment proxy routes use getRecording(id).backendId pattern consistent with all other API routes in the project
- DELETE route best-effort fetches attachment metadata to get filename for local file cleanup, then proceeds with backend delete regardless
- AttachedDocumentsCard uses controlled AlertDialog state (open/onOpenChange) rather than trigger-based pattern for programmatic delete target management

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TooltipTrigger asChild to render prop**
- **Found during:** Task 2 (AttachedDocumentsCard creation)
- **Issue:** Used shadcn-style `asChild` prop on TooltipTrigger, but project uses base-ui which uses `render` prop pattern
- **Fix:** Changed `<TooltipTrigger asChild>` to `<TooltipTrigger render={<span />}>`
- **Files modified:** src/components/recording/attached-documents-card.tsx
- **Verification:** TypeScript compiles cleanly
- **Committed in:** 33adb4e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor API difference in component library. No scope creep.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Full attachment flow operational: upload from detail page Info tab, view in card, delete with confirmation
- Post-recording dialog uploads now trigger backend text extraction for consistent behavior
- Phase 8 can access extracted text via backend GET /recordings/{id}/attachments/{aid}/text endpoint
- n_ctx=8192 (from Plan 01) ready for document context injection

---
*Phase: 07-document-attachments*
*Completed: 2026-03-19*

