# Phase 1: Recording and Transcription Pipeline - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can record audio in the browser via a global record button, manage recordings in a Recording Hub, assign them to projects (which triggers automatic transcription via the Python backend), and view completed transcripts with timestamps and speaker labels. Creating posts, extraction, and task management are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Recording UX
- Floating action button (FAB) in bottom-right corner, always visible on every screen
- While recording: FAB transforms into a red pulsing dot with elapsed time counter
- User can navigate the app while recording continues
- Tap FAB to stop recording — auto-saves immediately, no confirmation dialog
- Recording appears in hub as "Unassigned" after stop
- No pause/resume — stop only (simpler UX, fewer edge cases)

### Recording Hub
- Table/list view layout with columns: Title (auto-generated from date/time), Duration, Status, Project, Date
- Tab bar filtering across top: All | Unassigned | Processing | Ready — with count per tab
- Inline dropdown on the project column for unassigned recordings — shows existing projects + "Create new project"
- Assignment triggers automatic upload to Python backend for transcription (no manual "Transcribe" button)
- Status changes to "Processing" immediately upon assignment

### Backend Integration
- Polling for real-time status updates (frontend polls status endpoint every few seconds while processing)
- Direct multipart/form-data upload for audio files to FastAPI endpoint
- SQLite via better-sqlite3 for frontend metadata storage (recordings, projects, status) — local-first
- Next.js API routes proxy all requests to the Python backend — single origin, no CORS, clean separation
- Monorepo structure: Python backend and Next.js frontend in same project repo

### Transcript Display
- Chat-style speech bubbles for utterances
- Each speaker gets a distinct color for label and subtle bubble tint
- Inline muted timestamps per utterance (e.g., "0:32")
- Transcript shown on a dedicated recording detail page (click recording in hub → detail page with info + transcript)

### Claude's Discretion
- Auto-generated recording title format (date/time based)
- Exact speaker color palette
- Loading skeleton while transcript loads
- Error states (upload failure, transcription failure)
- Crash recovery implementation details for REC-03
- Polling interval and backoff strategy

</decisions>

<specifics>
## Specific Ideas

- Chat-style transcript bubbles similar to messaging apps — intuitive for reading conversations
- Tab bar with counts gives quick overview of recording pipeline status
- Auto-send on project assignment eliminates friction — one action triggers the whole pipeline

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing source code

### Established Patterns
- None yet — Phase 1 establishes the foundational patterns for the app

### Integration Points
- Python FastAPI backend (github.com/ZainAbbas97/allure-ai) — existing STT pipeline with Whisper
- Next.js API routes will proxy to this backend
- SQLite database shared concept between frontend (better-sqlite3) and backend
- Audio files stored on filesystem (~/.allure/recordings/)

</code_context>

<deferred>
## Deferred Ideas

- Audio playback synced to transcript (click utterance → seek) — v2 requirement (PLAY-01)
- Waveform visualization — v2 requirement (PLAY-02)
- Transcript editing — v2 requirement (REV-03)

</deferred>

---

*Phase: 01-recording-and-transcription-pipeline*
*Context gathered: 2026-03-12*
