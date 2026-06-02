---
phase: 06-speaker-management-recording-ux
verified: 2026-03-19T00:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
human_verification:
  - test: "Click pencil icon next to speaker name in stats panel"
    expected: "Input appears pre-filled with current name; Enter saves and name updates in all utterance bubbles"
    why_human: "UI interaction flow with optimistic update visible in DOM cannot be verified statically"
  - test: "Stop a recording and observe the post-recording dialog"
    expected: "Dialog appears immediately; upload starts in background; transcription status spinner is visible at dialog bottom"
    why_human: "Timing behavior (dialog opens while upload fires), live polling, and backdrop non-dismiss require runtime verification"
  - test: "Attempt to dismiss the post-recording dialog by clicking the backdrop or pressing Escape"
    expected: "Dialog stays open; only Save or Skip buttons close it"
    why_human: "Non-dismissible behavior depends on base-ui runtime handling of disablePointerDismissal and onKeyDown Escape prevention"
---

# Phase 6: Speaker Management & Recording UX Verification Report

**Phase Goal:** Users can rename speakers, assign roles, and complete a guided post-recording flow that names the recording, assigns a project, and optionally attaches documents -- all while transcription proceeds in the background
**Verified:** 2026-03-19
**Status:** passed
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can rename any speaker label (e.g. "Speaker 1" to "Alice") and the change reflects throughout the transcript | VERIFIED | `InlineEdit` wired in `SpeakerStatsPanel` calls `useUpdateSpeaker` with `customLabel`; `TranscriptView` builds `speakerMap` from `transcript.speakers` and passes `displayName` to every `UtteranceBubble` |
| 2 | User can assign a role to each speaker (e.g. "Product Manager") visible alongside their name | VERIFIED | Second `InlineEdit` in `SpeakerRow` calls `useUpdateSpeaker` with `role`; `UtteranceBubble` renders `{role}` between speaker name and timestamp when role prop is truthy |
| 3 | After stopping a recording, a popup appears where user can name the recording and assign it to a project | VERIFIED | `RecordingFAB.onRecordingCompleteRef` calls `openPostRecordingDialog`; `PostRecordingDialog` reads `showPostRecordingDialog` from Zustand and renders with `<Input>` name field and `<Select>` project dropdown |
| 4 | User can upload reference documents from the post-recording popup | VERIFIED | `FileDropZone` is embedded in `PostRecordingDialog`; Save handler POSTs `FormData` to `/api/recordings/${id}/documents`; documents API route saves to `public/recordings/{id}/docs/` |
| 5 | Transcription and diarization proceed in the background while the popup is open -- user does not wait | VERIFIED | Upload via `uploadRecording.mutate` fires BEFORE `openPostRecordingDialog`; dialog polls status via `useRecordingStatus` and shows spinner/checkmark/error in the status line |

**Score:** 5/5 success criteria verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/types/recording.ts` | Extended SpeakerStat with customLabel and role | VERIFIED | Lines 42-43: `customLabel?: string` and `role?: string` present |
| `src/components/transcript/inline-edit.tsx` | Reusable InlineEdit component | VERIFIED | Exports `InlineEdit`; 90 lines with pencil icon, click-to-edit, Enter/Escape/blur, auto-focus, trim+revert logic |
| `backend/main.py` | PATCH /recordings/{job_id}/speakers/{speaker_label} endpoint | VERIFIED | Lines 375-403: `@app.patch(...)` with URL decode, job validation, speaker find+modify, `update_job` persist |
| `backend/transcription.py` | assign_default_roles function | VERIFIED | Lines 358-374: `assign_default_roles` assigns "Presenter" to index 0, "Participant" to rest; called at line 441 in `run_transcription` |
| `src/app/api/recordings/[id]/speakers/[label]/route.ts` | Next.js PATCH proxy with cache invalidation | VERIFIED | Forwards to backend, calls `clearCachedTranscript(id)` on success |
| `src/hooks/use-recordings.ts` | useUpdateSpeaker mutation hook | VERIFIED | Lines 163-217: full optimistic mutation with cancel, snapshot, update, revert on error, invalidate on settle |
| `src/app/api/recordings/[id]/transcript/route.ts` | transformBackendData passes customLabel and role | VERIFIED | Lines 25-26: `customLabel: (s.custom_label as string) || ""` and `role: (s.role as string) || ""` |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/components/transcript/speaker-stats-panel.tsx` | Inline edit for speaker name and role | VERIFIED | Imports `InlineEdit`, `useUpdateSpeaker`; two `InlineEdit` instances per `SpeakerRow`; `recordingId` prop threaded through |
| `src/components/transcript/utterance-bubble.tsx` | displayName and role props displayed | VERIFIED | `UtteranceBubbleProps` includes `displayName?` and `role?`; `displayName || utterance.speaker` rendered; role rendered conditionally between name and timestamp |
| `src/components/transcript/speaker-badge.tsx` | displayName prop for custom label | VERIFIED | `SpeakerBadgeProps.displayName?: string` present; renders `displayName || speaker`; color mapping still uses original `speaker` via `getSpeakerIndex` |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/components/recording/post-recording-dialog.tsx` | PostRecordingDialog component | VERIFIED | Exports `PostRecordingDialog`; name input pre-filled from `pendingRecording.defaultTitle`; project Select with Unassigned; FileDropZone; transcription status line; Save + Skip buttons |
| `src/components/recording/file-drop-zone.tsx` | Drag-and-drop file upload area | VERIFIED | Exports `FileDropZone`; handles dragover/dragleave/drop and input change; accepts PDF/DOCX/DOC/TXT; shows file list with remove buttons |
| `src/stores/recording-store.ts` | Extended store with dialog state | VERIFIED | `showPostRecordingDialog` and `pendingRecording` in state; `openPostRecordingDialog`/`closePostRecordingDialog` actions; both excluded from Zustand `partialize` persistence |
| `src/components/recording/recording-fab.tsx` | FAB opens dialog and uploads in parallel | VERIFIED | `uploadRecording.mutate` fires first (line 28), then `openPostRecordingDialog` (line 37); `<PostRecordingDialog />` mounted inside FAB render |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/hooks/use-recordings.ts` | `/api/recordings/[id]/speakers/[label]` | `apiClient.patch` in `useUpdateSpeaker` | WIRED | Line 175: `apiClient.patch<...>(\`/api/recordings/${recordingId}/speakers/${encodeURIComponent(speakerLabel)}\`, body)` |
| `src/app/api/recordings/[id]/speakers/[label]/route.ts` | Backend `/recordings/{job_id}/speakers/{speaker_label}` | fetch proxy | WIRED | Lines 28-35: `fetch(\`${BACKEND_URL}/recordings/${recording.backendId}/speakers/${encodeURIComponent(label)}\`, ...)` |
| `src/components/transcript/speaker-stats-panel.tsx` | `useUpdateSpeaker` | `InlineEdit onSave -> mutation.mutate` | WIRED | Lines 63-68 and 75-80: both `InlineEdit` `onSave` callbacks call `updateSpeaker.mutate(...)` |
| `src/components/transcript/utterance-bubble.tsx` | `speakerMap` | prop lookup in `TranscriptView` | WIRED | `TranscriptView` lines 91-102 build `speakerMap` with `useMemo`; lines 134-135 pass `displayName` and `role` from `speakerMap.get(utterance.speaker)` |
| `src/components/recording/recording-fab.tsx` | `openPostRecordingDialog` in store | called on stop | WIRED | Line 37: `useRecordingStore.getState().openPostRecordingDialog(...)` called in `onRecordingCompleteRef` |
| `src/components/recording/recording-fab.tsx` | `useUploadRecording` | upload starts before dialog | WIRED | Line 28: `uploadRecording.mutate(formData, ...)` called before `openPostRecordingDialog` |
| `src/components/recording/post-recording-dialog.tsx` | `useRecordingStatus` | polling for transcription status | WIRED | Line 51: `useRecordingStatus(recordingId, !!pendingRecording)` feeds status line |
| `src/components/recording/post-recording-dialog.tsx` | `useRenameRecording` and `useAssignProject` | Save button | WIRED | Lines 89-103: `renameRecording.mutateAsync` and `assignProject.mutateAsync` called conditionally in `handleSave` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SPKR-01 | 06-01, 06-02 | User can edit speaker labels | SATISFIED | `InlineEdit` in `SpeakerStatsPanel` + `useUpdateSpeaker` + backend PATCH endpoint; changes propagate via `speakerMap` to all `UtteranceBubble` instances |
| SPKR-02 | 06-01, 06-02 | User can assign roles to speakers | SATISFIED | Second `InlineEdit` per speaker row for role; `assign_default_roles` sets initial values; role rendered in utterance bubbles |
| RUX-01 | 06-03 | After recording completes, a popup appears with name and project fields | SATISFIED | `PostRecordingDialog` opens via Zustand after `onRecordingCompleteRef` fires; name input and project Select confirmed present |
| RUX-02 | 06-03 | User can upload reference documents in the post-recording popup | SATISFIED | `FileDropZone` embedded in dialog; documents API route saves to disk |
| RUX-03 | 06-03 | Transcription and diarization proceed in the background while popup is open | SATISFIED | Upload fires before dialog opens; `useRecordingStatus` polls and reflects live status in dialog footer |

No orphaned Phase 6 requirements found. REQUIREMENTS.md traceability maps exactly SPKR-01, SPKR-02, RUX-01, RUX-02, RUX-03 to Phase 6 -- all accounted for.

---

## Anti-Patterns Found

No stub implementations, empty handlers, or placeholder components found in any Phase 6 files.

The single TypeScript error found (`src/app/api/recordings/__tests__/route.test.ts:53`) is a pre-existing test file incompatibility with Next.js `RequestInit` types. It is not in any Phase 6 file and does not affect production code.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/app/api/recordings/__tests__/route.test.ts` | TS type mismatch `AbortSignal \| null` | Info (pre-existing) | None -- test file only, not Phase 6 work |

---

## Human Verification Required

### 1. Speaker Rename Propagation

**Test:** Open a recording with a completed transcript. In the Speaker Statistics panel, click the pencil icon next to a speaker name. Type a new name and press Enter.
**Expected:** The name updates in the stats panel badge, and every utterance bubble for that speaker shows the new name immediately (optimistic update). After a brief moment, the server confirms and the cache refreshes.
**Why human:** Optimistic update timing, DOM mutation across components, and the cache invalidation refetch cycle require runtime verification.

### 2. Post-Recording Dialog Timing

**Test:** Start a recording, let it run for 5+ seconds, then stop it.
**Expected:** The dialog opens immediately with the name pre-filled (e.g., "Recording Mar 19, 2:30 PM"), the project dropdown shows existing projects, a spinner appears at the bottom labelled "Processing..." or "Transcribing...", and the recording appears in the Recording Hub while the dialog is still open.
**Why human:** Upload-before-dialog ordering, live status polling, and parallel background processing require runtime observation.

### 3. Non-Dismissible Dialog Behavior

**Test:** With the post-recording dialog open, click the backdrop area outside the dialog, then try pressing Escape.
**Expected:** The dialog remains open on both attempts. Only the Save or Skip buttons close it.
**Why human:** `disablePointerDismissal` prop and `onKeyDown` Escape prevention behavior depend on base-ui runtime handling and cannot be verified statically.

---

## Summary

All 14 must-have artifacts are present, substantive, and wired. The five ROADMAP.md success criteria are fully satisfied in code. All five requirement IDs (SPKR-01, SPKR-02, RUX-01, RUX-02, RUX-03) have direct implementation evidence. No stub implementations or orphaned artifacts were found.

Three behavioral items require human runtime verification: speaker rename propagation with optimistic updates, post-recording dialog opening timing with parallel upload, and the non-dismissible dialog behavior.

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_

