# Phase 10: Video Upload Pipeline - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Accept video file uploads (MP4, MOV), extract audio, fix duration metadata showing 0 for uploaded files, and run extracted audio through the existing STT pipeline. Video files are discarded after audio extraction — this is an audio-first app.

</domain>

<decisions>
## Implementation Decisions

### Upload Entry Point
- Use the existing upload button already in the UI — no new entry point needed
- Upload button should accept both audio (MP3, WAV, M4A, WebM) and video (MP4, MOV) files
- After upload, show the same post-recording dialog (title, project assignment, document upload)
- Original video file is discarded after audio extraction — only WAV is kept

### Duration Fix
- Sync duration from backend after processing completes — backend calculates correct duration via librosa
- Update frontend `duration_ms` from backend's transcript response `duration` field
- Fix applies to uploaded files only — live recordings keep using the client-side timer
- Single source of truth: backend's librosa-calculated duration for uploads

### Format & Validation
- Accepted video formats: MP4 and MOV (in addition to existing audio formats)
- File size limit: 500MB — prevent accidental huge uploads
- If video has no audio track: show clear error "This video has no audio — nothing to transcribe"
- Backend validates format and audio track presence

### Processing Feedback
- Same status flow as audio recordings — no additional "extracting audio" step shown to user
- Processing failures (corrupt file, unsupported codec, no audio) show as 'Error' status on the recording card in the hub page
- Click recording card to see error details

### Claude's Discretion
- FFmpeg flags for optimal audio extraction from video
- Error message wording and formatting
- How to detect missing audio tracks (ffprobe vs ffmpeg error handling)
- File size validation timing (client-side vs server-side)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `recording-fab.tsx`: Has upload trigger, creates FormData, sends to /api/recordings
- `/api/recordings/route.ts`: POST handler saves file, creates DB record, proxies to backend
- `backend/main.py` POST /recordings: Already accepts MP4, converts to WAV via FFmpeg
- `backend/audio_utils.py`: FFmpeg conversion to 16kHz mono WAV already exists
- `backend/transcription.py`: Duration calculated via `librosa.get_duration()` — correct value exists

### Established Patterns
- All audio conversion happens backend-side via FFmpeg → 16kHz mono PCM WAV
- Frontend stores `duration_ms` from client timer, backend calculates from audio file
- Status polling: frontend polls `/api/recordings/{id}/status` until complete
- Transcript sync: backend response cached in frontend SQLite `transcript_data`

### Integration Points
- Upload button in UI → needs to accept video MIME types
- `/api/recordings/route.ts` → needs to handle video files, pass through to backend
- Backend POST /recordings → already handles MP4, needs MOV added to validation
- Backend transcript response → `duration` field needs to be synced to frontend `duration_ms`
- Status/error display → recording card in hub page shows error status

</code_context>

<specifics>
## Specific Ideas

- Backend already does FFmpeg conversion for MP4 — most of the pipeline exists
- Duration 0 bug: frontend stores client timer value, but uploads have no timer. Fix by syncing backend's librosa duration after processing.
- Discard video after extraction — only the WAV matters for this app

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-video-upload-pipeline*
*Context gathered: 2026-03-26*
