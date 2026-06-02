# Architecture Patterns

**Domain:** Meeting intelligence features (playback sync, speaker stats, document attachments, clustering, product-focused generation)
**Researched:** 2026-03-18
**Scope:** v1.1 milestone -- new features integrating with existing v1.0 architecture

## Current Architecture Snapshot

```
Browser (Recording FAB)
  |
  v  POST /api/recordings (FormData: webm blob)
Next.js API Routes  <--->  Frontend SQLite (better-sqlite3)
  |                         (recordings, outcomes, tasks, documents)
  |  POST /recordings (proxy upload)
  v
FastAPI Backend  <--->  Backend SQLite (storage.py)
  |                     (jobs: status, result JSON, outcomes JSON)
  |-- Moonshine Voice STT
  |-- SpeechBrain ECAPA-TDNN + MeanShift diarization
  |-- Phi-4-mini via llama.cpp (extraction + doc generation)
  |
  v
Filesystem: backend/uploads/ (WAV), public/recordings/ (WebM)
```

**Key architectural facts from code reading:**
- Audio files saved as WebM in `public/recordings/{id}.webm` -- statically servable by Next.js
- Backend stores transcription results as JSON blob in `jobs.result` column
- Frontend transforms backend segments into `Utterance[]` at the API route level (`/api/recordings/[id]/transcript/route.ts`)
- Document generation happens synchronously in backend (`asyncio.to_thread`), persisted in frontend SQLite
- Zustand manages cross-component state (recording-store, evidence-highlight)
- TanStack Query handles all server state (recordings, transcripts, documents, outcomes)
- Backend speaker stats already computed but limited to `label`, `talk_time_pct`, `utterance_count`
- LLM context window set to 4096 tokens (`n_ctx=4096` in main.py)

---

## Component Map: New vs Modified

### New Components (Frontend)

| Component | File Path | Purpose |
|-----------|-----------|---------|
| AudioPlayer | `src/components/recording/audio-player.tsx` | HTML5 `<audio>` wrapper with seek controls, timeupdate relay |
| PlaybackStore | `src/stores/playback-store.ts` | Zustand store for playback time, play/pause, seek commands |
| SpeakerEditor | `src/components/transcript/speaker-editor.tsx` | Inline speaker label and role editing |
| SpeakerStatsPanel | `src/components/recording/speaker-stats-panel.tsx` | Per-speaker statistics display |
| MeetingStatsCard | `src/components/recording/meeting-stats-card.tsx` | Meeting-level statistics card |
| PostRecordingPopup | `src/components/recording/post-recording-popup.tsx` | Dialog after stop: name, project, doc upload |
| DocumentUpload | `src/components/recording/document-upload.tsx` | File drop zone for PDF/DOCX/TXT attachments |

### Modified Components (Frontend)

| Component | What Changes |
|-----------|-------------|
| `transcript-view.tsx` | Add click-to-seek dispatch, active utterance tracking by playback time |
| `utterance-bubble.tsx` | Add onClick handler for seek, active/playing CSS state |
| `recording-fab.tsx` | Open PostRecordingPopup instead of auto-saving on stop |
| `recordings/[id]/page.tsx` | Add AudioPlayer above tabs, speaker stats in Info tab, meeting stats card |
| `evidence-highlight.ts` | Extend `TabId` union type if new tabs needed |
| `use-recordings.ts` | Add speaker update mutation hook, attachment hooks |
| `use-documents.ts` | Add attachment upload mutation |
| `recording.ts` (types) | Extend Utterance with `role`, add Attachment type |
| `schema.sql` | Add `speaker_labels` table, `attachments` table |
| `recordings.ts` (db) | Speaker label CRUD, attachment CRUD functions |

### Modified Components (Backend)

| Component | What Changes |
|-----------|-------------|
| `transcription.py` | Replace MeanShift with AgglomerativeClustering in FastDiarizer; enrich `calculate_speaker_stats` with words/WPM/turns/pauses |
| `document_generation.py` | Accept document context parameter, rewrite prompts for product-focused generation |
| `main.py` | Add document upload endpoint, pass attachment context to generation endpoints |
| `storage.py` | Add attachment storage (column or separate tracking) |

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `PlaybackStore` (Zustand) | Current playback time, playing/paused state, seek requests | AudioPlayer, TranscriptView, UtteranceBubble |
| `AudioPlayer` | HTML5 `<audio>` element wrapper, timeupdate events, seek API | PlaybackStore |
| `TranscriptView` (modified) | Scroll-to-active utterance, click-to-seek dispatch | PlaybackStore, UtteranceBubble |
| `UtteranceBubble` (modified) | Click handler to seek, active highlight based on currentTime | PlaybackStore |
| `SpeakerEditor` | Inline rename of speaker labels and role assignment | Frontend API routes, TanStack Query |
| `SpeakerStatsPanel` | Display per-speaker time/words/WPM/turns stats | Transcript data (backend already returns speaker stats) |
| `MeetingStatsCard` | Display duration, processing time, speaker count, attachment count | Recording + transcript data |
| `PostRecordingPopup` | Dialog with title, project picker, document upload | RecordingFAB, upload hooks |
| `DocumentUpload` | File drop zone, validates PDF/DOCX/TXT, uploads to backend | Backend upload endpoint |

---

## Data Flow Changes

### 1. Audio Playback Sync

```
AudioPlayer --timeupdate--> PlaybackStore.currentTime (throttled to ~4Hz)
                                |
TranscriptView <--subscribe---- reads currentTime
  |                             binary search: find utterance where startTime <= currentTime < endTime
  |                             scrolls to it, applies "active" CSS class
  |
UtteranceBubble --onClick-----> PlaybackStore.seek(utterance.startTime)
                                |
AudioPlayer <--subscribe------- reads seekTo, sets audio.currentTime, nulls seekTo
```

**No backend changes needed.** Audio files already exist at `public/recordings/{id}.webm` -- directly accessible as static files at `/recordings/{id}.webm` from the browser.

**PlaybackStore shape:**
```typescript
interface PlaybackState {
  currentTime: number       // seconds, updated via timeupdate (throttled ~250ms)
  isPlaying: boolean
  duration: number
  seekTo: number | null     // set by click-to-seek, consumed by AudioPlayer
  recordingId: string | null
}

interface PlaybackActions {
  setCurrentTime: (t: number) => void
  setPlaying: (playing: boolean) => void
  seek: (time: number) => void
  clearSeek: () => void
  setDuration: (d: number) => void
  setRecordingId: (id: string | null) => void
}
```

**Why Zustand, not React context:** AudioPlayer sits in the recording detail page while transcript utterances are deep in the component tree. Zustand avoids prop drilling and re-render cascades -- identical pattern to the existing `useEvidenceHighlight` store.

**Active utterance detection:** Binary search over utterances array using `startTime/endTime` bounds. With typical meetings having 50-200 utterances, even linear scan is negligible, but binary search is cleaner.

### 2. Speaker Statistics

The backend already computes speaker stats in `transcription.py:calculate_speaker_stats()` (line 283-314), returning `label`, `talk_time_pct`, and `utterance_count`.

**What needs extending in `calculate_speaker_stats`:**

| New Field | Computation | Source |
|-----------|-------------|--------|
| `total_words` | `sum(len(seg.text.split()) for seg in speaker_segments)` | segment text |
| `wpm` | `total_words / (talk_time_minutes)` | derived |
| `turn_count` | Number of speaker-change boundaries into this speaker | segment order |
| `avg_turn_duration` | `total_talk_time / turn_count` | derived |
| `pause_count` | Gaps > 1s between consecutive segments of same speaker | segment times |
| `avg_pause_duration` | `total_pause_time / pause_count` | derived |

All computed from the existing `segments` list -- no new models or data sources.

**No new endpoints needed.** The enriched `speakers` array travels in the existing transcript response:
```
Backend transcript result -> jobs.result JSON -> GET /recordings/{backendId}/transcript
  -> Next.js API route transforms to frontend format -> frontend renders
```

The frontend `/api/recordings/[id]/transcript/route.ts` already passes through the full `data` object. The `speakers` array is available but currently unused by the transcript view. The new `SpeakerStatsPanel` will consume it.

### 3. Editable Speaker Labels

```sql
-- New table in frontend SQLite (schema.sql)
CREATE TABLE IF NOT EXISTS speaker_labels (
  id TEXT PRIMARY KEY,
  recording_id TEXT NOT NULL,
  original_label TEXT NOT NULL,    -- "Speaker 1" (from backend)
  custom_label TEXT,               -- "Alice" (user-set)
  role TEXT,                       -- "Product Manager" (user-set)
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (recording_id) REFERENCES recordings(id)
);
```

**Frontend-only storage.** The backend does not need speaker names -- it operates on cluster IDs. Speaker labels are a UI concern.

**New API routes:**
- `PUT /api/recordings/{id}/speakers` -- upsert speaker label/role overrides
- `GET /api/recordings/{id}/speakers` -- read overrides for a recording

**Rendering logic:** `TranscriptView` and `UtteranceBubble` apply overrides at render time:
```typescript
const displayLabel = speakerOverrides[utterance.speaker]?.customLabel || utterance.speaker
```

### 4. Post-Recording Popup

**Current flow:**
```
Stop Recording -> RecordingFAB auto-uploads -> creates DB record -> toast
```

**New flow:**
```
Stop Recording -> PostRecordingPopup opens (Dialog)
  |-- Title input (pre-filled with auto-generated title)
  |-- Project dropdown (optional)
  |-- Document attachment drop zone (optional, multiple files)
  |-- "Save" button
  |
  v
On Save:
  1. POST /api/recordings (existing: file + metadata + projectId)
  2. If documents attached: POST /api/recordings/{id}/attachments (new)
  3. Backend begins STT processing in background (existing flow)
```

**Key change in `recording-fab.tsx`:** Instead of calling `uploadRecording.mutate()` directly in the `onRecordingComplete` callback, it opens the popup dialog and passes the `AudioRecorderResult` to it. The popup handles the upload on confirm.

### 5. Document Attachments

**Storage approach:** Files on filesystem, metadata in SQLite (same pattern as audio).

```sql
-- Frontend SQLite
CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY,
  recording_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (recording_id) REFERENCES recordings(id)
);
```

**File storage location:** `public/recordings/attachments/{recordingId}/{filename}`

**Backend text extraction flow:**
```
Frontend: POST /api/recordings/{id}/attachments (multipart)
  |
  v
Next.js API route: saves file locally, creates DB record, proxies to backend
  |
  v
Backend: POST /recordings/{job_id}/attachments (new endpoint)
  |-- Saves file to backend/uploads/attachments/{job_id}/
  |-- Extracts text:
  |     PDF -> subprocess: pdftotext (poppler-utils)
  |     DOCX -> python-docx library
  |     TXT -> direct read
  |-- Stores extracted text in jobs table (new column: attachment_context TEXT)
  |-- Returns: { id, filename, extracted_text_length }
```

**Why extract text on backend, not frontend:** Python has robust PDF/DOCX libraries (pdftotext, python-docx). Node.js PDF parsing is unreliable and bloated. The backend already manages Python dependencies.

### 6. Document Context Injection into Generation

**Modified generation flow:**

```
Frontend: POST /api/recordings/{id}/generate-prd
  |
  v
Next.js API route: fetches recording, forwards to backend (existing pattern)
  |
  v
Backend: POST /recordings/{job_id}/generate-prd
  |-- Reads job from storage (existing)
  |-- Reads attachment_context from job (NEW)
  |-- Builds prompt:
  |     System: PRD_SYSTEM_PROMPT (rewritten for product focus)
  |     User: "Reference documents:\n{attachment_text}\n\n
  |            Meeting outcomes:\n{formatted_outcomes}"
  |-- Calls LLM (existing)
```

**Context window concern:** Current `n_ctx=4096` in main.py is tight. Typical breakdown:
- System prompt: ~300 tokens
- Outcomes (10 items): ~800 tokens
- Available for attachments: ~900 tokens (after leaving room for output)
- Output max: ~2000 tokens

**Recommendation: increase `n_ctx` to 8192.** Phi-4-mini supports up to 16K context. M3 has sufficient memory. This gives ~4000 tokens for attachment context, enough for 2-3 pages of extracted text.

If attachment text exceeds the budget, use smart truncation:
1. Extract document headings/titles first
2. Include first paragraph of each section
3. Truncate remaining text at token limit

### 7. AgglomerativeClustering

**Current code (transcription.py line 146-147):**
```python
clustering = MeanShift()
labels = clustering.fit_predict(embedding_matrix)
```

**Replacement:**
```python
from sklearn.cluster import AgglomerativeClustering

clustering = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=0.7,    # cosine distance threshold -- tune on test recordings
    metric="cosine",
    linkage="average",
)
labels = clustering.fit_predict(embedding_matrix)
```

**Why AgglomerativeClustering over MeanShift:**
- MeanShift auto-estimates bandwidth, which often over-segments (creates phantom speakers) or under-segments (merges distinct speakers)
- AgglomerativeClustering with cosine metric + average linkage is the standard approach for speaker embeddings (used by pyannote, resemblyzer)
- `distance_threshold` gives direct, interpretable control over speaker separation sensitivity
- `n_clusters=None` with `distance_threshold` auto-determines speaker count (same capability as MeanShift)

**Integration is surgical:** Only `FastDiarizer.diarize()` changes. Everything downstream (alignment, snapping, remapping, merging, stats) operates on the same `[{start, end, speaker}]` format and needs zero changes.

**Risk: threshold tuning.** The `distance_threshold=0.7` is a starting point for ECAPA-TDNN cosine embeddings. Must validate on 3-5 test recordings with known speaker counts. This is the primary risk in this feature.

### 8. Product-Focused Diagram Generation

**Current problem:** Prompts instruct the LLM to "generate from meeting outcomes" which makes it diagram the meeting process itself, not the product being discussed.

**Fix is prompt engineering, no architectural change:**

Current prompt (document_generation.py):
```
"Generate a Mermaid flowchart from the meeting outcomes below"
```

New prompt direction:
```
"The meeting outcomes below describe a product or system being discussed.
 Identify the product and generate a Mermaid flowchart showing:
 - The product's main user journey (not the meeting flow)
 - Key decision points in the product's workflow
 - System interactions and data flow

 If reference documents are provided, use them to enrich the diagram
 with accurate entity names, relationships, and workflow steps."
```

Same change applies to ERD prompt -- diagram the data model of the product discussed, not meeting entities.

---

## Patterns to Follow

### Pattern 1: Zustand Store for Cross-Component Coordination
**What:** Dedicated Zustand store when multiple components need shared reactive state
**When:** Audio playback time must coordinate player, transcript view, and utterance highlight
**Example:** `PlaybackStore` mirrors the proven `EvidenceHighlightStore` pattern already in the codebase
```typescript
export const usePlaybackStore = create<PlaybackState & PlaybackActions>()((set) => ({
  currentTime: 0,
  isPlaying: false,
  seekTo: null,
  // actions...
}))
```

### Pattern 2: Frontend-Only Data Augmentation
**What:** Store UI-only data (speaker names, roles) in frontend SQLite without backend round-trip
**When:** Data is user-facing only and backend does not need it for processing
**Why:** Avoids coupling backend to UI concerns. Backend remains stateless for speaker identity.

### Pattern 3: Throttled Store Updates for Media Events
**What:** Throttle `timeupdate` events before writing to Zustand store
**When:** HTML5 Audio `timeupdate` fires 4-15 times/second depending on browser
**Why:** Prevents excessive re-renders in transcript view
```typescript
const throttledUpdate = useRef(
  throttle((time: number) => usePlaybackStore.getState().setCurrentTime(time), 250)
)
```

### Pattern 4: Proxy Pattern for Backend Calls (Existing)
**What:** All backend calls go through Next.js API routes, never direct from browser
**When:** Always -- this is the established pattern throughout the codebase
**Why:** Keeps backend URL private, allows frontend to augment/transform data (e.g., add attachment context, transform segment format to Utterance format)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Bidirectional Audio State Sync
**What:** Both `<audio>` element and Zustand store as "sources of truth" for playback time
**Why bad:** Creates feedback loops (store updates audio, audio updates store, repeat)
**Instead:** `<audio>` element is the source of truth for current time. Store is a read-cache + command channel. AudioPlayer reads `seekTo` from store, applies it to `audio.currentTime`, then nulls `seekTo`. Never write `currentTime` from store back to audio element.

### Anti-Pattern 2: Storing Attachment Files in SQLite
**What:** Saving PDF/DOCX binary content as BLOBs in the database
**Why bad:** Bloats database, SQLite not optimized for large BLOBs
**Instead:** Files on filesystem (`public/recordings/attachments/{recordingId}/`), only metadata in SQLite. Same pattern already used for audio files.

### Anti-Pattern 3: Re-processing Backend for Speaker Renames
**What:** Sending speaker label changes to backend, re-running diarization
**Why bad:** Diarization is expensive (seconds), renames are cosmetic
**Instead:** Speaker label overrides live only in frontend SQLite. TranscriptView applies overrides at render time via a lookup map.

### Anti-Pattern 4: Extracting Document Text on Frontend
**What:** Parsing PDFs in Node.js / Next.js API routes
**Why bad:** Node.js PDF libraries are large, unreliable, and poorly maintained. Python has battle-tested tools (pdftotext from poppler, python-docx).
**Instead:** Upload raw files to backend, extract text in Python, store extracted text. Backend already has the dependency ecosystem for this.

---

## Integration Points Summary

| Feature | Frontend Changes | Backend Changes | New Endpoints | DB Schema Changes |
|---------|-----------------|-----------------|---------------|-------------------|
| Audio Playback Sync | AudioPlayer, PlaybackStore, TranscriptView mod, UtteranceBubble mod | None | None | None |
| Speaker Stats Display | SpeakerStatsPanel, MeetingStatsCard | Enrich `calculate_speaker_stats()` return value | None (data in existing transcript response) | None |
| Speaker Label Editing | SpeakerEditor, speaker_labels DB CRUD | None | `PUT/GET /api/recordings/{id}/speakers` (frontend-only routes) | `speaker_labels` table (frontend SQLite) |
| Post-Recording Popup | PostRecordingPopup, RecordingFAB mod | None | None (reuses existing upload) | None |
| Document Attachments | DocumentUpload, attachment hooks | Upload endpoint, text extraction | `POST/GET/DELETE /api/recordings/{id}/attachments` + backend mirror | `attachments` table (frontend + backend) |
| Context-Aware Generation | Generate PRD/Diagram routes pass context | Accept + prepend context in prompts | Modified existing generation endpoints | `attachment_context` column (backend jobs) |
| AgglomerativeClustering | None | Replace MeanShift in `FastDiarizer.diarize()` | None | None |
| Product-Focused Prompts | None | Rewrite system prompts in `document_generation.py` | None | None |

---

## Build Order (Dependency-Driven)

```
Phase 1: Foundation (independent, can parallelize)
  |-- AgglomerativeClustering (backend-only, isolated change in FastDiarizer)
  |-- PlaybackStore + AudioPlayer (frontend-only, zero backend deps)
  |-- Speaker stats enrichment (backend-only, extends existing calculate_speaker_stats)

Phase 2: Depends on Phase 1
  |-- Transcript sync with playback (requires PlaybackStore)
  |-- Speaker stats display (requires enriched stats from backend)
  |-- Meeting stats card (requires enriched transcript data)

Phase 3: Independent feature cluster
  |-- Post-recording popup (modifies RecordingFAB flow)
  |-- Speaker label editing (frontend-only CRUD, new DB table)

Phase 4: Depends on Phase 3 for upload UX
  |-- Document attachments (file upload, storage, backend text extraction)

Phase 5: Depends on Phase 4 for context data
  |-- Document context injection into generation prompts
  |-- Product-focused prompt rewrite
  |-- Increase n_ctx to 8192
```

**Rationale:**
- Playback sync and clustering are highest-risk, highest-complexity -- go first to surface problems early
- Speaker stats and meeting stats are low-risk extensions of existing data -- pair with playback
- Post-recording popup is a UX flow change that gates document upload -- must precede attachments
- Document attachments have the most new infrastructure (tables, endpoints, file handling, text extraction) -- need popup flow first
- Prompt improvements are lowest risk and depend on attachment context being available -- go last, easy to iterate

---

## Scalability Considerations

| Concern | Current (FYP) | Notes |
|---------|---------------|-------|
| Audio file size | WebM ~128kbps, 1hr = ~56MB | Fine for local filesystem |
| Attachment size | PDF/DOCX typically < 5MB | Cap at 10MB per file, 3 files per recording |
| LLM context window | 4096 tokens (current) | Increase to 8192 for attachment context |
| Playback latency | Local file served by Next.js static | Zero network latency concern |
| Speaker stats computation | O(n) over segments | Trivial even for long meetings |
| Clustering threshold tuning | Manual `distance_threshold` parameter | Expose as optional setting if needed |
| Text extraction | Synchronous per-file | Fine for 1-3 small documents |

## Sources

- All findings based on direct code reading of the Allure AI codebase (v1.0 as of commit a7c2a34)
- AgglomerativeClustering for speaker diarization: sklearn standard, widely used with ECAPA-TDNN cosine embeddings (pyannote, resemblyzer implementations) -- HIGH confidence
- HTML5 Audio API (timeupdate, currentTime, seek): Web standard -- HIGH confidence
- Phi-4-mini context window: confirmed `n_ctx=4096` in main.py line 80, model supports up to 16K per Hugging Face model card -- HIGH confidence
- Zustand store pattern: proven in existing codebase (evidence-highlight.ts, recording-store.ts) -- HIGH confidence

