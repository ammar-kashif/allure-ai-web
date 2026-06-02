# Phase 6: Speaker Management & Recording UX - Research

**Researched:** 2026-03-19
**Domain:** Inline editing UX, post-recording dialog flow, background upload orchestration
**Confidence:** HIGH

## Summary

Phase 6 adds two distinct feature areas to an existing Next.js 16 + Python FastAPI application: (1) speaker label renaming and role assignment in the transcript view, and (2) a post-recording popup dialog that captures recording metadata while transcription proceeds in the background.

The codebase already has all the primitives needed: `SpeakerStatsPanel` with per-speaker rows, `SpeakerBadge` for colored labels, `UtteranceBubble` displaying speaker names, a `Dialog` component from base-ui/shadcn, Zustand stores for recording state, TanStack Query mutations for API calls, Sonner for toasts, and a `Select` component for dropdowns. The backend stores transcript results as JSON with a `speakers` array and `segments` array -- both need new fields for custom labels and roles.

**Primary recommendation:** Implement speaker editing as a frontend-first lookup map pattern (speaker label -> custom name/role), persisted to backend via a new PATCH endpoint. Implement the post-recording dialog by intercepting the `onRecordingCompleteRef` callback in `RecordingFAB` to show the dialog while simultaneously starting the upload.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Edit location: speaker stats panel at the top of the Transcript tab -- each speaker row has an always-visible pencil icon
- Click pencil icon -> inline text field replaces the label; Enter or blur saves
- Renames propagate to all utterance bubbles in the transcript and speaker stats panel
- Renames do NOT propagate to Outcomes tab -- outcomes keep original labels since they're extracted artifacts
- Persistence: backend + frontend -- send rename to Python backend which updates the transcript data, frontend reflects updated names on save
- Roles are auto-assigned from a predefined list by the backend during transcription/diarization pipeline
- Users can override roles with free text input (not a dropdown) -- same inline edit pattern as names
- Roles displayed in both places: smaller muted text below the speaker name in the stats panel, and next to the speaker name + timestamp in utterance bubbles
- Role edits persisted the same way as name edits -- backend + frontend, stored alongside the transcript
- Centered shadcn Dialog appears immediately after stopping a recording
- Fields: recording name (text input), project assignment (select from existing projects), reference document upload (file drop zone)
- Recording name pre-filled with date + time default ("Recording Mar 19, 2:30 PM") -- user can overwrite
- Project field: select from existing projects only, no inline project creation; includes "Unassigned" option
- Skip/dismiss behavior: recording is saved with auto-generated defaults (name, no project, no docs) -- nothing is lost, user can edit later from recording detail page
- Dialog stays open until user explicitly clicks Save or Skip -- no auto-close
- Audio upload to backend begins immediately when recording stops, before dialog opens -- transcription starts in parallel with user filling out fields
- Status shown as a subtle text line at the bottom of the dialog: "Transcribing..." with a spinner, updates to "Transcription complete" when done
- After dialog closes (save or skip), if processing still running: toast notification ("Transcription in progress") + recording shows "Processing" status in Recording Hub list
- User can navigate freely after closing dialog -- existing status polling in Recording Hub tracks completion

### Claude's Discretion
- Predefined role list for auto-assignment (reasonable defaults like "Participant", "Presenter", etc.)
- Exact inline edit component styling (input field transitions, save/cancel affordances)
- File upload zone design in the post-recording dialog (drag-and-drop styling, accepted file types)
- Backend API design for speaker rename/role update endpoints
- How to handle role display when role is empty/unset
- Toast notification timing and wording

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPKR-01 | User can edit speaker labels (rename "Speaker 1" to "John") | Speaker label lookup map pattern, inline edit in SpeakerStatsPanel, propagation to UtteranceBubble, backend PATCH endpoint for speaker updates |
| SPKR-02 | User can assign roles to speakers (e.g., "Product Manager") | Role field added to speaker data, auto-assignment in backend pipeline, inline free-text edit in stats panel, role display in utterance bubbles |
| RUX-01 | After recording completes, a popup appears with name and project fields | PostRecordingDialog component using existing Dialog primitive, intercept RecordingFAB stop flow |
| RUX-02 | User can upload reference documents in the post-recording popup | File drop zone in dialog, store files temporarily, attach to recording on save |
| RUX-03 | Transcription and diarization proceed in the background while popup is open | Upload starts before dialog opens, status polling shown in dialog footer, toast on close if still processing |

</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.3 | UI framework | Project standard |
| Next.js | 16.1.6 | Full-stack framework | Project standard |
| Zustand | 5.0.11 | State management | Project pattern for cross-component state |
| TanStack Query | 5.90.21 | Server state / mutations | Project pattern for all API calls |
| @base-ui/react | 1.2.0 | Headless UI primitives (Dialog, Select) | Project standard, shadcn uses this |
| Sonner | 2.0.7 | Toast notifications | Project standard |
| Lucide React | 0.577.0 | Icons (Pencil, Check, X, Upload) | Project standard |
| date-fns | 4.1.0 | Date formatting | Already used in generateRecordingTitle |
| FastAPI | (backend) | Python API server | Project backend |

### Supporting (No New Dependencies Needed)
This phase requires zero new npm or pip packages. Everything needed is already installed.

### File Upload Note
For RUX-02 (reference document upload), the native HTML `<input type="file">` with drag-and-drop via standard DOM events is sufficient. No need for a library like `react-dropzone` -- the upload zone is a simple single-use component inside the dialog. Store the File objects in component state, attach to FormData on save.

## Architecture Patterns

### Recommended Project Structure
```
src/
  components/
    transcript/
      speaker-stats-panel.tsx    # MODIFY: add inline edit for name + role
      speaker-badge.tsx          # MODIFY: accept displayName prop
      utterance-bubble.tsx       # MODIFY: show role, use display name
      inline-edit.tsx            # NEW: reusable inline text edit component
    recording/
      recording-fab.tsx          # MODIFY: intercept stop to show dialog
      post-recording-dialog.tsx  # NEW: post-recording metadata dialog
      file-drop-zone.tsx         # NEW: drag-and-drop file upload area
  hooks/
    use-recordings.ts            # MODIFY: add speaker update mutation
  stores/
    recording-store.ts           # MODIFY: add post-recording dialog state
  types/
    recording.ts                 # MODIFY: extend SpeakerStat with role, customLabel
backend/
  transcription.py               # MODIFY: add role auto-assignment
  main.py                        # MODIFY: add speaker update endpoint
  storage.py                     # No changes needed (update_job handles JSON)
```

### Pattern 1: Speaker Label Lookup Map
**What:** Instead of mutating utterance data directly, maintain a `speakerDisplayMap` that maps original labels to custom names/roles. Components read through this map.
**When to use:** When the same speaker label appears in many utterances and you need consistent renaming.
**Example:**
```typescript
// In transcript view or a shared hook
type SpeakerDisplayInfo = {
  originalLabel: string   // "Speaker 1"
  customLabel: string     // "Alice"
  role: string           // "Product Manager"
}

// Build from transcript.speakers data
const speakerMap = new Map<string, SpeakerDisplayInfo>()
for (const speaker of transcript.speakers) {
  speakerMap.set(speaker.label, {
    originalLabel: speaker.label,
    customLabel: speaker.custom_label || speaker.label,
    role: speaker.role || "Participant",
  })
}

// UtteranceBubble reads: speakerMap.get(utterance.speaker)
```

### Pattern 2: Optimistic Inline Edit with Backend Sync
**What:** When user edits a speaker name/role, update the local TanStack Query cache immediately (optimistic update), then send PATCH to backend. Revert on error.
**When to use:** Inline edits that should feel instant.
**Example:**
```typescript
const updateSpeaker = useMutation({
  mutationFn: ({ recordingId, speakerLabel, customLabel, role }) =>
    apiClient.patch(`/api/recordings/${recordingId}/speakers/${encodeURIComponent(speakerLabel)}`, {
      custom_label: customLabel,
      role,
    }),
  onMutate: async (variables) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ["transcript", variables.recordingId] })
    // Snapshot previous
    const previous = queryClient.getQueryData(["transcript", variables.recordingId])
    // Optimistically update cache
    queryClient.setQueryData(["transcript", variables.recordingId], (old) => {
      // Update the speaker in the speakers array
      return { ...old, speakers: old.speakers.map(s =>
        s.label === variables.speakerLabel
          ? { ...s, custom_label: variables.customLabel, role: variables.role }
          : s
      )}
    })
    return { previous }
  },
  onError: (_err, variables, context) => {
    queryClient.setQueryData(["transcript", variables.recordingId], context.previous)
    toast.error("Failed to update speaker")
  },
})
```

### Pattern 3: Upload-Then-Dialog Flow
**What:** When recording stops, immediately start the upload (fire-and-forget mutation), then open the dialog. The dialog shows upload/transcription status via polling.
**When to use:** The post-recording flow where upload should not block the user.
**Example:**
```typescript
// In RecordingFAB, replace the current onRecordingCompleteRef callback:
onRecordingCompleteRef.current = (result) => {
  // 1. Start upload immediately (runs in background)
  const formData = new FormData()
  formData.append("file", result.blob, `${result.recordingId}.webm`)
  formData.append("recordingId", result.recordingId)
  formData.append("title", result.title) // default title
  formData.append("durationMs", String(result.durationMs))
  uploadRecording.mutate(formData)

  // 2. Open post-recording dialog with the result data
  useRecordingStore.getState().openPostRecordingDialog({
    recordingId: result.recordingId,
    defaultTitle: result.title,
    durationMs: result.durationMs,
  })
}
```

### Anti-Patterns to Avoid
- **Mutating utterance text directly for renames:** The `utterance.speaker` field should stay as the original label. Use a display lookup map instead. This keeps the data model clean and avoids costly re-renders of every utterance.
- **Blocking upload on dialog completion:** Upload must start before the dialog opens. The dialog only collects metadata (name, project, docs) that gets PATCH'd onto the already-created recording.
- **Using a global Zustand store for inline edit state:** The edit state (which field is being edited, current input value) is local to the SpeakerStatsPanel component. Use React useState, not Zustand.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dialog component | Custom modal | Existing `Dialog` from `@/components/ui/dialog.tsx` | Already styled, accessible, uses base-ui primitives |
| Select/dropdown | Custom dropdown | Existing `Select` from `@/components/ui/select.tsx` | Already styled, keyboard accessible |
| Toast notifications | Custom notification system | Sonner `toast()` | Already integrated project-wide |
| Optimistic updates | Manual cache management | TanStack Query `onMutate`/`onError` pattern | Built-in support, handles rollback |
| Status polling | Custom setInterval | `useRecordingStatus` hook with `refetchInterval` | Already exists and stops on completion |

## Common Pitfalls

### Pitfall 1: getSpeakerIndex Breaking on Custom Names
**What goes wrong:** The current `getSpeakerIndex()` extracts a number from the speaker string via regex (`/(\d+)/`). If you replace "Speaker 1" with "Alice" in the data, the color assignment breaks (returns 0 for all).
**Why it happens:** The function assumes speaker labels always contain a number.
**How to avoid:** Keep original labels in the data. The display map provides custom names, but color assignment always uses the original `utterance.speaker` field. Never overwrite `utterance.speaker` with the custom name.
**Warning signs:** All speakers showing the same color (indigo) after renaming.

### Pitfall 2: Dialog Closing on Overlay Click
**What goes wrong:** base-ui Dialog closes when clicking the backdrop overlay by default. User accidentally closes the post-recording dialog and metadata is lost.
**Why it happens:** Default Dialog behavior.
**How to avoid:** Set `modal={true}` and handle close explicitly. The base-ui Dialog supports `onOpenChange` -- only allow closing via Save/Skip buttons, not backdrop click. Use `dismissible={false}` or equivalent prop on the Dialog root.
**Warning signs:** Dialog disappearing unexpectedly during testing.

### Pitfall 3: Race Condition Between Upload and Save
**What goes wrong:** User clicks Save with a custom title before the initial upload POST completes. The recording might be created with the default title, then the PATCH with the custom title arrives -- or vice versa.
**Why it happens:** Upload starts immediately with default title; Save sends a PATCH with user-entered title.
**How to avoid:** The upload POST creates the recording with the auto-generated title. The Save button sends a PATCH to update title, projectId, and attach documents. These are sequential operations on the same recording ID, so no race condition as long as PATCH waits for the recording to exist. Use `onSuccess` of the upload mutation or check recording existence before PATCH.
**Warning signs:** Recording showing default title after user entered a custom one.

### Pitfall 4: Backend Speaker Update Without Proper JSON Handling
**What goes wrong:** The backend `result` field is stored as JSON text. Updating a single speaker's label requires reading the full result, modifying the speakers array, and writing it back. Concurrent updates could overwrite each other.
**Why it happens:** SQLite JSON storage without row-level locking on nested fields.
**How to avoid:** The backend endpoint should read-modify-write in a single transaction. Since this is a single-user desktop app with SQLite, this is low risk, but wrap in a transaction for safety.
**Warning signs:** Speaker rename reverting after a page refresh.

### Pitfall 5: File Upload in Dialog vs. Phase 7 Document Attachments
**What goes wrong:** Phase 6 adds a file drop zone for reference documents. Phase 7 (DOC-01, DOC-02, DOC-03) adds full document attachment with text extraction. Building too much document infrastructure in Phase 6 creates duplication.
**Why it happens:** Scope overlap between "upload reference docs in post-recording popup" and "full document attachment system."
**How to avoid:** Phase 6 should ONLY store the uploaded files (save to disk, record file paths in the recording). It should NOT extract text or display documents on the recording detail page. Keep it minimal: accept files, save them, done. Phase 7 builds the full document management layer.
**Warning signs:** Building a documents table, text extraction, or document list UI in Phase 6.

## Code Examples

### Inline Edit Component
```typescript
// src/components/transcript/inline-edit.tsx
"use client"

import { useState, useRef, useEffect, type KeyboardEvent } from "react"
import { Pencil } from "lucide-react"
import { cn } from "@/lib/utils"

interface InlineEditProps {
  value: string
  onSave: (newValue: string) => void
  className?: string
  inputClassName?: string
  placeholder?: string
}

export function InlineEdit({ value, onSave, className, inputClassName, placeholder }: InlineEditProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  const save = () => {
    const trimmed = draft.trim()
    if (trimmed && trimmed !== value) {
      onSave(trimmed)
    } else {
      setDraft(value) // revert
    }
    setEditing(false)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") save()
    if (e.key === "Escape") { setDraft(value); setEditing(false) }
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={handleKeyDown}
        className={cn("rounded border px-1.5 py-0.5 text-sm outline-none focus:ring-2 focus:ring-ring", inputClassName)}
        placeholder={placeholder}
      />
    )
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className={cn("group inline-flex items-center gap-1.5", className)}
    >
      <span>{value}</span>
      <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
    </button>
  )
}
```

### Backend Speaker Update Endpoint
```python
# Add to backend/main.py
@app.patch("/recordings/{job_id}/speakers/{speaker_label}")
async def update_speaker(job_id: str, speaker_label: str, request: Request):
    """Update a speaker's custom label and/or role."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcript not ready")

    body = await request.json()
    result = job["result"]

    # Update speaker in stats
    for speaker in result.get("speakers", []):
        if speaker["label"] == speaker_label:
            if "custom_label" in body:
                speaker["custom_label"] = body["custom_label"]
            if "role" in body:
                speaker["role"] = body["role"]
            break

    # Update speaker in segments (only custom_label, keep original label for color mapping)
    # Actually: segments keep original "speaker" field. Only speakers array gets custom_label/role.

    update_job(job_id, result=result)
    return {"ok": True}
```

### Post-Recording Dialog State Extension
```typescript
// Extension to recording-store.ts
interface PostRecordingState {
  showPostRecordingDialog: boolean
  pendingRecording: {
    recordingId: string
    defaultTitle: string
    durationMs: number
  } | null
}

interface PostRecordingActions {
  openPostRecordingDialog: (data: PostRecordingState["pendingRecording"]) => void
  closePostRecordingDialog: () => void
}

// Add to existing store:
// showPostRecordingDialog: false,
// pendingRecording: null,
// openPostRecordingDialog: (data) => set({ showPostRecordingDialog: true, pendingRecording: data }),
// closePostRecordingDialog: () => set({ showPostRecordingDialog: false, pendingRecording: null }),
```

### Role Auto-Assignment in Backend
```python
# Add to transcription.py after remap_speaker_labels

DEFAULT_ROLES = ["Presenter", "Participant", "Interviewer", "Interviewee", "Moderator"]

def assign_default_roles(stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign default roles based on talk time heuristics.

    Speaker with highest talk time gets "Presenter", rest get "Participant".
    """
    for i, speaker in enumerate(stats):
        if i == 0:  # highest talk_time_pct (stats are sorted desc)
            speaker["role"] = "Presenter"
        else:
            speaker["role"] = "Participant"
        speaker["custom_label"] = ""  # empty = use original label
    return stats
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| shadcn Dialog using Radix | shadcn Dialog using @base-ui/react | shadcn v4 (2025) | Dialog API is slightly different -- uses `DialogPrimitive.Root`, `Popup` instead of `Content` |
| react-dropzone for file upload | Native drag-and-drop events | Always available | No extra dependency needed for simple file drops |

**Note on base-ui Dialog:** The project's Dialog component wraps `@base-ui/react/dialog`, not Radix. The API uses `DialogPrimitive.Popup` (not `DialogContent` from Radix). The `open` prop and `onOpenChange` callback control visibility. To prevent backdrop-click dismissal, check `dismissible` prop on `DialogPrimitive.Root` or handle via `onOpenChange` filtering.

## Open Questions

1. **Next.js API Route for Speaker Updates**
   - What we know: The frontend calls Next.js API routes (e.g., `/api/recordings/[id]`), which proxy to the Python backend. Speaker updates need both a Next.js route and a backend endpoint.
   - What's unclear: Should the Next.js route for speaker updates proxy to backend, or should it also cache the updated transcript data locally (in `transcript_data` column)?
   - Recommendation: Proxy to backend and invalidate the transcript query cache. The `cacheTranscript` function in `recordings.ts` could optionally be updated, but it's simpler to just invalidate and re-fetch.

2. **File Storage for Reference Documents (RUX-02)**
   - What we know: Files are uploaded in the post-recording dialog. Phase 7 handles full document management.
   - What's unclear: Where to store uploaded files and how to associate them with recordings before Phase 7's document table exists.
   - Recommendation: Save files to `public/recordings/{recordingId}/docs/` on disk. Store file paths as a JSON array in a new `reference_docs` column on the recordings table (or just save to disk and let Phase 7 formalize the schema). Minimal approach: just save files to disk, no DB schema changes in Phase 6.

3. **Preventing Dialog Dismiss on Backdrop Click**
   - What we know: base-ui Dialog has `dismissible` behavior. The user decision says dialog stays open until Save/Skip.
   - Recommendation: Set `dismissible={false}` on the Dialog root, or filter `onOpenChange` to only allow programmatic closing. Test both approaches during implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.0.18 + React Testing Library 16.3.2 |
| Config file | `vitest.config.ts` |
| Quick run command | `npx vitest run --reporter=verbose` |
| Full suite command | `npx vitest run --reporter=verbose` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPKR-01 | Clicking pencil shows input, Enter saves, name propagates to bubbles | unit | `npx vitest run src/components/transcript/__tests__/speaker-stats-panel.test.tsx -x` | No -- Wave 0 |
| SPKR-01 | Backend speaker update endpoint persists custom_label | unit | `npx vitest run src/hooks/__tests__/use-speaker-update.test.ts -x` | No -- Wave 0 |
| SPKR-02 | Role displays in stats panel and utterance bubbles | unit | `npx vitest run src/components/transcript/__tests__/utterance-bubble.test.tsx -x` | Yes (extend) |
| RUX-01 | Dialog opens after stopping recording, Save/Skip work | unit | `npx vitest run src/components/recording/__tests__/post-recording-dialog.test.tsx -x` | No -- Wave 0 |
| RUX-02 | File drop zone accepts files, stores in state | unit | `npx vitest run src/components/recording/__tests__/post-recording-dialog.test.tsx -x` | No -- Wave 0 |
| RUX-03 | Status text shows in dialog, toast on close if still processing | unit | `npx vitest run src/components/recording/__tests__/post-recording-dialog.test.tsx -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run --reporter=verbose`
- **Per wave merge:** `npx vitest run --reporter=verbose`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/components/transcript/__tests__/speaker-stats-panel.test.tsx` -- covers SPKR-01, SPKR-02 inline edit
- [ ] `src/components/recording/__tests__/post-recording-dialog.test.tsx` -- covers RUX-01, RUX-02, RUX-03
- [ ] `src/components/transcript/__tests__/inline-edit.test.tsx` -- covers reusable inline edit component
- [ ] Extend `src/components/transcript/__tests__/utterance-bubble.test.tsx` -- add role display tests

## Sources

### Primary (HIGH confidence)
- Codebase inspection: all files listed in Architecture Patterns section were read directly
- `speaker-stats-panel.tsx`, `speaker-badge.tsx`, `utterance-bubble.tsx` -- current component structure
- `recording-fab.tsx`, `use-audio-recorder.ts` -- current recording stop flow
- `recording-store.ts` -- current Zustand store shape
- `use-recordings.ts` -- existing TanStack Query mutation patterns
- `dialog.tsx`, `select.tsx` -- existing UI primitives
- `transcription.py` -- backend pipeline producing speaker stats
- `storage.py` -- backend JSON storage pattern
- `schema.sql` -- frontend SQLite schema
- `main.py` -- backend API endpoints

### Secondary (MEDIUM confidence)
- base-ui Dialog `dismissible` prop behavior -- inferred from base-ui patterns, verify during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all primitives exist
- Architecture: HIGH -- patterns directly derived from existing codebase conventions
- Pitfalls: HIGH -- identified from actual code inspection (getSpeakerIndex regex, Dialog close behavior, upload race condition)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- no external dependencies changing)

