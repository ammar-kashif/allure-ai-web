---
phase: 01-recording-and-transcription-pipeline
verified: 2026-03-12T00:00:00Z
status: gaps_found
score: 12/14 must-haves verified
gaps:
  - truth: "Assigning a project triggers automatic upload to Python backend (no manual transcribe button)"
    status: failed
    reason: "useAssignProject mutation only PATCHes local DB (projectId + status: processing). The PATCH route (/api/recordings/[id]) has no backend proxy logic. Audio is never forwarded to FastAPI when a user assigns a project from the Hub. Backend proxy only fires during the initial POST upload, but recordings are always uploaded as unassigned (no projectId). Result: status shows Processing but FastAPI never receives the file."
    artifacts:
      - path: "src/hooks/use-recordings.ts"
        issue: "useAssignProject calls PATCH /api/recordings/{id} with {projectId, status: processing} — no file forwarding"
      - path: "src/app/api/recordings/[id]/route.ts"
        issue: "PATCH handler updates DB fields only — no BACKEND_URL, no fetch to FastAPI"
    missing:
      - "PATCH /api/recordings/[id] must proxy the saved audio file to FastAPI when projectId is set"
      - "OR useAssignProject must re-POST the file as FormData with projectId to /api/recordings (which already has proxy logic)"
      - "Either approach must store backendId returned from FastAPI so status/transcript polling works"

  - truth: "Processing status updates display in real-time (STT-04: queued -> processing -> complete)"
    status: partial
    reason: "Polling infrastructure is wired and working. However, because audio is never forwarded to FastAPI on assignment (see gap above), the backendId is never set. Without backendId, the status route falls back to returning local DB status and never actually polls FastAPI. The real-time update chain is broken at the source."
    artifacts:
      - path: "src/app/api/recordings/[id]/status/route.ts"
        issue: "Returns local status when recording.backendId is null (line 19-21) — which it always will be after assignment-only PATCH"
    missing:
      - "Depends on the same fix as above — once audio is forwarded and backendId stored, polling will work correctly"

human_verification:
  - test: "Start recording, stop, assign project — verify status actually transitions through Processing to Ready"
    expected: "Status badge should move from Unassigned -> Processing -> Ready as FastAPI processes the audio"
    why_human: "Requires running dev server + FastAPI backend to confirm end-to-end proxy flow after the backend-upload gap is fixed"
  - test: "Dual audio capture flow — verify Chrome tab picker appears and system audio is mixed"
    expected: "On start recording, browser shows screen-share picker; selecting a tab with audio results in both mic and tab audio in the recording"
    why_human: "Browser permission flow and mixed-stream behavior cannot be verified programmatically"
---

# Phase 1: Recording and Transcription Pipeline — Verification Report

**Phase Goal:** Frontend scaffolding, audio recording, backend integration, transcript display — completing the Record -> Upload -> Transcribe -> View pipeline.
**Verified:** 2026-03-12
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Vitest runs with happy-dom environment | VERIFIED | `vitest.config.ts` sets `environment: 'happy-dom'`, `setupFiles`, path alias `@` |
| 2  | fake-indexeddb and MSW configured for tests | VERIFIED | `src/test/setup.ts` imports `fake-indexeddb/auto` and wires MSW server lifecycle |
| 3  | All 9 test skeleton files exist | VERIFIED | All paths confirmed present with substantive describe blocks |
| 4  | User can tap global FAB from any screen to start recording | VERIFIED | `RecordingFAB` rendered in `(dashboard)/layout.tsx`; uses `useAudioRecorder` |
| 5  | FAB shows red pulsing dot with elapsed time while recording | VERIFIED | `recording-fab.tsx` applies `animate-pulse bg-red-500` + `formatDuration(elapsedSeconds * 1000)` when `isRecording` |
| 6  | Recording continues across page navigation | VERIFIED | `mediaRecorderRef` is module-level (outside React), survives re-renders and navigation |
| 7  | Tapping FAB stops recording and auto-saves to IndexedDB then DB | VERIFIED | `onstop` handler assembles blob from IndexedDB, `onRecordingCompleteRef` in FAB POSTs FormData to `/api/recordings` |
| 8  | Audio chunks survive browser crash (crash recovery) | VERIFIED | `recording-store.ts` `onRehydrateStorage` sets `needsRecovery=true`; `use-audio-recorder.ts` calls `checkForRecovery()` on mount |
| 9  | SQLite database initializes with recordings and projects tables | VERIFIED | `src/lib/db/index.ts` creates DB, runs `schema.sql`; schema has both tables with FK |
| 10 | API routes proxy uploads to FastAPI when projectId provided at POST time | VERIFIED | `POST /api/recordings` with `projectId` proxies to `${BACKEND_URL}/recordings`, stores `backendId` |
| 11 | Unassigned recordings saved locally without backend proxy | VERIFIED | POST without `projectId` skips `if (projectId)` block entirely |
| 12 | Recording Hub displays table with Title, Duration, Status, Project, Date | VERIFIED | `RecordingHub` renders shadcn `Table` with all 5 columns via `RecordingRow` |
| 13 | **Assigning a project triggers automatic upload to Python backend** | **FAILED** | `useAssignProject` only PATCHes local DB — no file forwarded to FastAPI; `backendId` never set |
| 14 | **STT-04: Status updates in real-time (queued -> processing -> complete)** | **PARTIAL** | Polling hook and 3s `refetchInterval` are wired; but status route returns local value when `backendId` is null — chain is broken until upload gap is fixed |

**Score: 12/14 truths verified**

---

### Required Artifacts

#### Plan 01-00: Test Infrastructure

| Artifact | Status | Evidence |
|----------|--------|----------|
| `vitest.config.ts` | VERIFIED | Exists; `happy-dom`, `setupFiles`, `@` alias, `include` pattern |
| `src/test/setup.ts` | VERIFIED | `@testing-library/jest-dom/vitest`, `fake-indexeddb/auto`, MSW lifecycle |
| `src/hooks/__tests__/use-audio-recorder.test.ts` | VERIFIED | Substantive — real tests plus todo stubs |
| `src/lib/audio/__tests__/chunk-store.test.ts` | VERIFIED | Exists with describe block |
| `src/components/recording/__tests__/recording-fab.test.tsx` | VERIFIED | Exists with describe block |
| `src/components/recording/__tests__/recording-hub.test.tsx` | VERIFIED | Exists with describe block |
| `src/components/recording/__tests__/project-assignment.test.tsx` | VERIFIED | Exists with describe block |
| `src/hooks/__tests__/use-recordings.test.ts` | VERIFIED | Substantive — 6 real tests |
| `src/app/api/recordings/__tests__/route.test.ts` | VERIFIED | Substantive — 4 real tests |
| `src/components/transcript/__tests__/transcript-view.test.tsx` | VERIFIED | Exists with describe block |
| `src/components/transcript/__tests__/utterance-bubble.test.tsx` | VERIFIED | Exists with describe block |

#### Plan 01-01: Audio Recording Pipeline

| Artifact | Status | Evidence |
|----------|--------|----------|
| `src/stores/recording-store.ts` | VERIFIED | Exports `useRecordingStore`; persist middleware with `allure-recording` key; `onRehydrateStorage` sets `needsRecovery` |
| `src/lib/audio/chunk-store.ts` | VERIFIED | Exports `saveAudioChunk`, `getAudioChunks`, `clearAudioChunks`, `getIncompleteRecordingIds`; uses `idb`, compound index |
| `src/lib/audio/recovery.ts` | VERIFIED | Exports `checkForRecovery`, `recoverRecording`, `discardRecovery` |
| `src/hooks/use-audio-recorder.ts` | VERIFIED | MediaRecorder wrapper; module-level refs; `saveAudioChunk` on `ondataavailable`; crash recovery check on mount |
| `src/components/recording/recording-fab.tsx` | VERIFIED | `'use client'`; toggles start/stop; red pulse when recording; `useAudioRecorder` + `useUploadRecording` wired |
| `src/types/recording.ts` | VERIFIED | All 4 types: `RecordingStatus`, `Recording`, `Project`, `Utterance`, `Transcript` |

#### Plan 01-02: Data Layer and API Proxy

| Artifact | Status | Evidence |
|----------|--------|----------|
| `src/lib/db/index.ts` | VERIFIED | `getDb()` singleton; WAL mode; FK enforcement; reads `schema.sql` |
| `src/lib/db/recordings.ts` | VERIFIED | Exports `getRecordings`, `getRecording`, `createRecording`, `updateRecording`, `getRecordingCounts`; snake_case -> camelCase mapping |
| `src/app/api/recordings/route.ts` | VERIFIED | `GET` returns list; `POST` saves file locally + optional FastAPI proxy |
| `src/hooks/use-recordings.ts` | VERIFIED | Exports `useRecordings`, `useRecording`, `useRecordingStatus`, `useTranscript`, `useUploadRecording`, `useAssignProject` |

#### Plan 01-03: Recording Hub UI

| Artifact | Status | Evidence |
|----------|--------|----------|
| `src/components/recording/recording-hub.tsx` | VERIFIED | Tabs (All/Unassigned/Processing/Ready with counts); table; `ProcessingPoller`; toast on completion |
| `src/components/recording/project-assignment.tsx` | VERIFIED | Select dropdown listing projects; `+ Create new project` option; inline project creation flow |
| `src/components/recording/status-badge.tsx` | VERIFIED | Exists and wired in `RecordingRow` |

#### Plan 01-04: Transcript Detail Page

| Artifact | Status | Evidence |
|----------|--------|----------|
| `src/components/transcript/transcript-view.tsx` | VERIFIED | Exports `TranscriptView`; maps utterances to `UtteranceBubble`; empty state; same-speaker grouping |
| `src/components/transcript/utterance-bubble.tsx` | VERIFIED | Exports `UtteranceBubble`; 5-color palette cycling by speaker index; `M:SS` timestamp format |
| `src/app/(dashboard)/recordings/[id]/page.tsx` | VERIFIED | Client component; `useRecording` + `useRecordingStatus` + `useTranscript`; state-dependent rendering for unassigned/processing/ready/error |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `recording-fab.tsx` | `use-audio-recorder.ts` | `useAudioRecorder` hook | WIRED | Import and destructure at line 13 |
| `use-audio-recorder.ts` | `chunk-store.ts` | `saveAudioChunk` on `ondataavailable` | WIRED | `ondataavailable` calls `saveAudioChunk(recordingId, event.data)` at line 167 |
| `use-audio-recorder.ts` | `recording-store.ts` | `useRecordingStore` | WIRED | Destructured at top of hook |
| `(dashboard)/layout.tsx` | `recording-fab.tsx` | `RecordingFAB` rendered in root layout | WIRED | `<RecordingFAB />` at line 24 |
| `use-recordings.ts` | `/api/recordings/[id]/status` | `refetchInterval` polling every 3s | WIRED | `refetchInterval` returns 3000ms while processing, `false` on ready/error |
| `project-assignment.tsx` | `use-recordings.ts` | `useAssignProject` on project selection | WIRED | `assignProject.mutate({recordingId, projectId})` called in hub |
| **`use-recordings.ts`** | **FastAPI via PATCH** | **Assignment triggers backend upload** | **NOT WIRED** | `useAssignProject` PATCH sets projectId/status locally only; no file forwarded to backend |
| `recordings/[id]/page.tsx` | `use-recordings.ts` | `useRecording` and `useTranscript` | WIRED | Both hooks imported and called at lines 21, 33 |
| `transcript-view.tsx` | `utterance-bubble.tsx` | Maps utterances to `UtteranceBubble` | WIRED | `utterances.map(... => <UtteranceBubble .../>)` |
| `use-recordings.ts` | `/api/recordings/[id]/transcript` | TanStack Query fetch | WIRED | `apiClient.get(\`/api/recordings/${recordingId}/transcript\`)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REC-01 | 01-00, 01-01 | One-tap global record button from any screen | SATISFIED | Global FAB in dashboard layout |
| REC-02 | 01-00, 01-01 | Browser captures mic audio via Web Audio API | SATISFIED | `getUserMedia({audio:true})` + optional system audio mix via `getDisplayMedia` |
| REC-03 | 01-00, 01-01 | Recording auto-saves with crash recovery | SATISFIED | IndexedDB chunk storage + `onRehydrateStorage` recovery detection |
| REC-04 | 01-00, 01-02, 01-03 | Recording Hub with status display | SATISFIED | `/recordings` page with table and status badges |
| REC-05 | 01-00, 01-03 | Assign recording to project | SATISFIED | Inline project dropdown; create-new-project inline |
| REC-06 | 01-00, 01-01, 01-03 | Unassigned recordings stay local | SATISFIED | POST without projectId skips backend proxy; status stays unassigned |
| STT-01 | 01-00, 01-02 | Recording sent to Python backend for Whisper | BLOCKED | POST with projectId proxies file — but normal flow (assign from Hub) never sends file to backend (see gap) |
| STT-02 | 01-00, 01-04 | Transcript includes utterance timestamps | SATISFIED | `UtteranceBubble` shows `M:SS` inline timestamp from `utterance.startTime` |
| STT-03 | 01-00, 01-04 | Speaker diarization labels | SATISFIED | Speaker label rendered; `getSpeakerIndex` maps "Speaker N" to color |
| STT-04 | 01-00, 01-02 | Processing status updates in real-time | PARTIAL | 3s polling wired; broken because `backendId` is never set after assignment-only PATCH |

**Orphaned requirements:** None — all 10 phase IDs (REC-01 to REC-06, STT-01 to STT-04) are claimed in plan frontmatter and accounted for.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | No empty implementations, return nulls, or TODO stubs in production source files |

Only `placeholder=` HTML attribute found (in input field for project creation — correct usage, not a stub).

---

### Human Verification Required

#### 1. End-to-End Assignment -> Transcription Flow (post-fix)

**Test:** After the backend-upload gap is fixed: Start a recording, stop it, assign to a project, and watch the status badge.
**Expected:** Status transitions Unassigned -> Processing -> Ready; toast fires "Transcription complete!" when done.
**Why human:** Requires running dev server + FastAPI backend; the real-time polling behavior and toast timing cannot be verified programmatically.

#### 2. Dual Audio Capture

**Test:** Click the FAB; in the Chrome screen-share picker, select a browser tab; speak into mic while audio plays on the tab.
**Expected:** The saved recording contains both mic and tab audio mixed together.
**Why human:** `getDisplayMedia` permission flow, Chrome tab picker UI, and mixed-stream quality are browser-environment-only behaviors.

#### 3. Crash Recovery UX

**Test:** Start a recording, force-kill the browser tab, reopen the app.
**Expected:** A toast appears offering to Recover or Discard the incomplete recording.
**Why human:** Requires real browser crash simulation; `needsRecovery` flag and toast rendering cannot be exercised in vitest/jsdom.

---

### Gaps Summary

**One root cause, two broken truths.**

The audio recording pipeline has a gap in the assignment-to-backend upload path. The design intent is: user assigns a project -> file is sent to FastAPI -> backendId stored -> polling updates status. The implementation delivers the first half (assignment updates local DB) but the second half (forwarding audio to FastAPI) was never wired.

**Why it happened:** The POST route correctly proxies when `projectId` is included at upload time. However, the normal user flow always uploads first (unassigned, no projectId) and assigns later. The PATCH route that handles the assignment step has no backend proxy logic and never sets `backendId`. As a result:

1. `useAssignProject` sets status to "processing" locally — but FastAPI never processes anything.
2. The status polling route correctly falls back to local status when `backendId` is null, so it never transitions to "ready".

**Fix options (either works):**
- Add backend proxy logic to PATCH `/api/recordings/[id]`: when `projectId` is newly set, read the saved file, POST it to FastAPI, store `backendId`.
- Change `useAssignProject` to call POST `/api/recordings` (which already has proxy logic) with the `projectId` + the saved file re-attached as FormData.

All other pipeline stages — recording capture, crash recovery, SQLite storage, Recording Hub UI, tabs, project assignment UI, and transcript display — are fully implemented and wired.

---

_Verified: 2026-03-12_
_Verifier: Claude (gsd-verifier)_

