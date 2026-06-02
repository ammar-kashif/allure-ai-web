# Phase 6: Speaker Management & Recording UX - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can rename speakers, assign roles, and complete a guided post-recording flow that names the recording, assigns a project, and optionally attaches documents -- all while transcription proceeds in the background. Speaker statistics and audio playback are Phase 5. Document text extraction is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Speaker Label Editing
- Edit location: speaker stats panel at the top of the Transcript tab — each speaker row has an always-visible pencil icon
- Click pencil icon → inline text field replaces the label; Enter or blur saves
- Renames propagate to all utterance bubbles in the transcript and speaker stats panel
- Renames do NOT propagate to Outcomes tab — outcomes keep original labels since they're extracted artifacts
- Persistence: backend + frontend — send rename to Python backend which updates the transcript data, frontend reflects updated names on save

### Speaker Roles
- Roles are auto-assigned from a predefined list by the backend during transcription/diarization pipeline
- Users can override roles with free text input (not a dropdown) — same inline edit pattern as names
- Roles displayed in both places: smaller muted text below the speaker name in the stats panel, and next to the speaker name + timestamp in utterance bubbles
- Role edits persisted the same way as name edits — backend + frontend, stored alongside the transcript

### Post-Recording Popup
- Centered shadcn Dialog appears immediately after stopping a recording
- Fields: recording name (text input), project assignment (select from existing projects), reference document upload (file drop zone)
- Recording name pre-filled with date + time default ("Recording Mar 19, 2:30 PM") — user can overwrite
- Project field: select from existing projects only, no inline project creation; includes "Unassigned" option
- Skip/dismiss behavior: recording is saved with auto-generated defaults (name, no project, no docs) — nothing is lost, user can edit later from recording detail page
- Dialog stays open until user explicitly clicks Save or Skip — no auto-close

### Background Processing
- Audio upload to backend begins immediately when recording stops, before dialog opens — transcription starts in parallel with user filling out fields
- Status shown as a subtle text line at the bottom of the dialog: "○ Transcribing..." with a spinner, updates to "✓ Transcription complete" when done
- After dialog closes (save or skip), if processing still running: toast notification ("Transcription in progress") + recording shows "Processing" status in Recording Hub list
- User can navigate freely after closing dialog — existing status polling in Recording Hub tracks completion

### Claude's Discretion
- Predefined role list for auto-assignment (reasonable defaults like "Participant", "Presenter", etc.)
- Exact inline edit component styling (input field transitions, save/cancel affordances)
- File upload zone design in the post-recording dialog (drag-and-drop styling, accepted file types)
- Backend API design for speaker rename/role update endpoints
- How to handle role display when role is empty/unset
- Toast notification timing and wording

</decisions>

<specifics>
## Specific Ideas

- Speaker stats panel edit UX: pencil icon always visible (not hover-to-reveal) for discoverability
- Post-recording dialog mockup: name field at top, project dropdown below, doc upload area, status line at bottom, Skip + Save buttons
- "Save with defaults" philosophy — Skip never discards data, just uses auto-generated values
- Roles auto-assigned from backend means the UI always shows a role, even before user edits

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SpeakerBadge` component (`speaker-badge.tsx`): Renders colored pill with speaker name — extend to show editable name + role
- `speakerColors` and `getSpeakerIndex` (`utterance-bubble.tsx`): Color palette and index lookup — reuse for consistent coloring
- `UtteranceBubble` component: Already displays speaker name and timestamp — add role display next to name
- `SpeakerStatsPanel` component (`speaker-stats-panel.tsx`): Shows per-speaker metrics — add inline edit for name and role
- `Dialog` component from shadcn/ui (`components/ui/dialog.tsx`): Ready to use for post-recording popup
- `useRecordingStore` (Zustand): Tracks isRecording, currentRecordingId — extend for post-recording dialog state
- `RecordingFAB`: Current stop handler auto-uploads via `onRecordingCompleteRef` — intercept to show dialog first

### Established Patterns
- Zustand for cross-component state (evidence-highlight, recording-store, audio-playback) — follow for speaker edit state
- TanStack Query mutations for data persistence (useUploadRecording) — use for speaker rename/role API calls
- Backend stores transcript as JSON with speakers array — extend speaker objects with `customLabel` and `role` fields
- Toast notifications via Sonner for async feedback — use for upload/processing status

### Integration Points
- `RecordingFAB.stopRecording()`: Currently triggers immediate upload — needs to open dialog instead, with upload happening in parallel
- Backend `transcription.py`: Add role auto-assignment to diarization pipeline, add speaker update endpoint
- `recording-store.ts`: May need new state for "post-recording dialog open" and "pending recording data"
- `SpeakerStat` type: Add `role: string` field
- `Utterance` type: Speaker field maps to renamed labels via lookup

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-speaker-management-recording-ux*
*Context gathered: 2026-03-19*

