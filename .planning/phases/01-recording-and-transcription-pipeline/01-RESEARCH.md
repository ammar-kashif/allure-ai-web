# Phase 1: Recording and Transcription Pipeline - Research

**Researched:** 2026-03-12
**Domain:** Browser audio recording, local-first storage, FastAPI integration, transcript display
**Confidence:** HIGH (core technologies well-understood; patterns verified against official docs)

## Summary

Phase 1 establishes the entire frontend-backend integration foundation for Allure. The technical domain spans four areas: (1) browser audio capture via MediaRecorder API, (2) local-first metadata storage with better-sqlite3, (3) Next.js API route proxying to FastAPI for audio upload and transcription, and (4) a chat-style transcript display with speaker labels and timestamps. The most critical risk is the end-to-end pipeline from browser recording to Whisper transcription -- this must be proven working on day 1-2 before any UI polish.

The crash recovery requirement (REC-03) is best solved by combining two strategies: using MediaRecorder's `timeslice` parameter to receive audio chunks every few seconds and persisting them to IndexedDB immediately, plus using Zustand's `persist` middleware to track recording metadata (start time, status, chunk count) in localStorage. If the browser crashes, IndexedDB retains the audio chunks and localStorage retains the recording metadata, enabling recovery on next page load.

**Primary recommendation:** Build the full record-upload-transcribe-display pipeline end-to-end first with minimal UI, then layer on the Recording Hub table, status polling, and transcript bubbles. Integration before aesthetics.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Floating action button (FAB) in bottom-right corner, always visible on every screen
- While recording: FAB transforms into a red pulsing dot with elapsed time counter
- User can navigate the app while recording continues
- Tap FAB to stop recording -- auto-saves immediately, no confirmation dialog
- Recording appears in hub as "Unassigned" after stop
- No pause/resume -- stop only (simpler UX, fewer edge cases)
- Table/list view layout with columns: Title (auto-generated from date/time), Duration, Status, Project, Date
- Tab bar filtering across top: All | Unassigned | Processing | Ready -- with count per tab
- Inline dropdown on the project column for unassigned recordings -- shows existing projects + "Create new project"
- Assignment triggers automatic upload to Python backend for transcription (no manual "Transcribe" button)
- Status changes to "Processing" immediately upon assignment
- Polling for real-time status updates (frontend polls status endpoint every few seconds while processing)
- Direct multipart/form-data upload for audio files to FastAPI endpoint
- SQLite via better-sqlite3 for frontend metadata storage (recordings, projects, status) -- local-first
- Next.js API routes proxy all requests to the Python backend -- single origin, no CORS, clean separation
- Monorepo structure: Python backend and Next.js frontend in same project repo
- Chat-style speech bubbles for utterances
- Each speaker gets a distinct color for label and subtle bubble tint
- Inline muted timestamps per utterance (e.g., "0:32")
- Transcript shown on a dedicated recording detail page (click recording in hub -> detail page with info + transcript)

### Claude's Discretion
- Auto-generated recording title format (date/time based)
- Exact speaker color palette
- Loading skeleton while transcript loads
- Error states (upload failure, transcription failure)
- Crash recovery implementation details for REC-03
- Polling interval and backoff strategy

### Deferred Ideas (OUT OF SCOPE)
- Audio playback synced to transcript (click utterance -> seek) -- v2 requirement (PLAY-01)
- Waveform visualization -- v2 requirement (PLAY-02)
- Transcript editing -- v2 requirement (REV-03)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REC-01 | User can start recording with one tap from any screen (global record button) | FAB component pattern with Zustand for global recording state; MediaRecorder API initialization |
| REC-02 | Browser captures laptop microphone audio via Web Audio API | MediaRecorder API with `audio/webm;codecs=opus` MIME type; `getUserMedia` for mic access |
| REC-03 | Recording auto-saves to filesystem with crash recovery | IndexedDB for audio chunk persistence via `timeslice` + Zustand persist for metadata; reassemble on recovery |
| REC-04 | Recording Hub displays all recordings with status (Unassigned, Processing, Ready) | better-sqlite3 local DB for recording metadata; TanStack Table for list view; tab filtering |
| REC-05 | User can assign a recording to a project (create new or attach existing session) | Inline dropdown component; assignment triggers upload via Next.js API route to FastAPI |
| REC-06 | Unassigned recordings are private to the creating user | Local-first storage means unassigned recordings exist only in browser IndexedDB + local SQLite |
| STT-01 | Recording is sent to Python backend for Whisper STT processing | Next.js route handler proxies multipart/form-data upload to FastAPI endpoint |
| STT-02 | Transcript includes timestamps for each utterance | Backend returns timestamped utterances; frontend renders inline timestamps |
| STT-03 | Transcript includes speaker diarization labels | Backend returns speaker labels; frontend maps to color-coded chat bubbles |
| STT-04 | Processing status updates display in real-time | TanStack Query `refetchInterval` polling with dynamic interval; stop on completion |
</phase_requirements>

## Standard Stack

### Core (Phase 1 specific)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| MediaRecorder API | Browser native | Audio capture from microphone | Built into all modern browsers; no library needed. Use `audio/webm;codecs=opus` |
| better-sqlite3 | ^12.4 | Local SQLite for frontend metadata | Synchronous, fastest Node.js SQLite binding; works in Next.js API routes/server components |
| @tanstack/react-query | ^5.62 | Server state, polling | `refetchInterval` handles status polling; caching and error states for all API calls |
| @tanstack/react-table | ^8.20 | Recording Hub table | Headless table with sorting, filtering; Tailwind-friendly |
| zustand | ^5.0 | Recording state + crash recovery | Global recording state (isRecording, elapsed time); `persist` middleware for crash recovery metadata |
| idb | ^8.0 | IndexedDB wrapper | Promise-based IndexedDB access for storing audio Blob chunks; tiny (1.2KB), typed |
| date-fns | ^4.1 | Timestamp formatting | Format recording dates, durations, utterance timestamps |
| sonner | ^1.7 | Toast notifications | Error/success feedback for upload, transcription status changes |

### Already Decided (from STACK.md)

| Library | Version | Purpose |
|---------|---------|---------|
| Next.js | ^15.1 | App Router framework |
| React | ^19.0 | UI library |
| TypeScript | ^5.7 | Type safety |
| Tailwind CSS | ^4.0 | Styling |
| shadcn/ui | latest | Component library (Table, Tabs, Button, Badge, DropdownMenu, Select, Sheet) |
| Zod | ^3.24 | Schema validation for API responses |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| idb (IndexedDB wrapper) | Raw IndexedDB API | idb is 1.2KB and adds Promises + types; raw API is callback-based and error-prone |
| better-sqlite3 | Prisma with SQLite | Prisma adds ORM overhead; better-sqlite3 is direct SQL which is simpler for this use case |
| Polling (TanStack Query) | Server-Sent Events (SSE) | SSE would need FastAPI setup + Next.js proxy support; polling is simpler and adequate for FYP |
| IndexedDB for audio chunks | localStorage | localStorage has 5-10MB limit; audio files easily exceed this; IndexedDB has no practical limit |

**Installation (Phase 1 additions):**
```bash
# Phase 1 specific packages
npm install idb

# better-sqlite3 (native addon - requires node-gyp)
npm install better-sqlite3
npm install -D @types/better-sqlite3
```

## Architecture Patterns

### Recommended Project Structure (Phase 1)

```
src/
  app/
    (dashboard)/
      layout.tsx               # Main app layout with FAB recording button
      page.tsx                  # Dashboard / redirect to recordings
      recordings/
        page.tsx                # Recording Hub (table + tabs)
        [id]/
          page.tsx              # Recording detail page (info + transcript)
    api/
      recordings/
        route.ts               # GET list, POST upload (proxy to FastAPI)
        [id]/
          route.ts              # GET/PATCH single recording (proxy)
          status/
            route.ts            # GET processing status (proxy)
          transcript/
            route.ts            # GET transcript (proxy)
      projects/
        route.ts                # GET/POST projects (local SQLite)
  components/
    recording/
      recording-fab.tsx         # Global floating action button
      recording-hub.tsx         # Hub table with tabs
      recording-row.tsx         # Table row component
      project-assignment.tsx    # Inline project dropdown
      status-badge.tsx          # Status indicator (Unassigned/Processing/Ready)
    transcript/
      transcript-view.tsx       # Chat-bubble transcript display
      utterance-bubble.tsx      # Single speaker utterance
  hooks/
    use-audio-recorder.ts       # MediaRecorder wrapper with IndexedDB persistence
    use-recordings.ts           # TanStack Query hooks (list, detail, status polling)
    use-projects.ts             # TanStack Query hooks for projects
  lib/
    api/
      client.ts                 # Fetch wrapper for API calls
    db/
      index.ts                  # better-sqlite3 database singleton
      schema.sql                # Table definitions
      recordings.ts             # Recording CRUD operations
      projects.ts               # Project CRUD operations
    audio/
      chunk-store.ts            # IndexedDB audio chunk storage (idb)
      recovery.ts               # Crash recovery logic
    utils.ts                    # cn() helper, formatDuration(), formatTimestamp()
  stores/
    recording-store.ts          # Zustand: isRecording, elapsed, currentRecordingId
```

### Pattern 1: Audio Recording with Crash Recovery

**What:** MediaRecorder captures audio in timed chunks, each chunk is immediately persisted to IndexedDB. Zustand persist tracks recording metadata in localStorage. On crash/refresh, recovery logic checks for incomplete recordings and reassembles audio from IndexedDB chunks.

**When to use:** Always -- this is the REC-03 implementation.

**Example:**

```typescript
// hooks/use-audio-recorder.ts
import { useRecordingStore } from '@/stores/recording-store';
import { saveAudioChunk, getAudioChunks, clearAudioChunks } from '@/lib/audio/chunk-store';

const CHUNK_INTERVAL_MS = 3000; // Save a chunk every 3 seconds

export function useAudioRecorder() {
  const { setRecording, setElapsed, currentRecordingId } = useRecordingStore();
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mimeType = 'audio/webm;codecs=opus';
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      throw new Error('audio/webm;codecs=opus not supported in this browser');
    }

    const recorder = new MediaRecorder(stream, { mimeType });
    const recordingId = crypto.randomUUID();

    recorder.ondataavailable = async (event) => {
      if (event.data.size > 0) {
        await saveAudioChunk(recordingId, event.data);
      }
    };

    recorder.onstop = async () => {
      const chunks = await getAudioChunks(recordingId);
      const blob = new Blob(chunks, { type: mimeType });
      // Save complete recording to local DB, clear IndexedDB chunks
      await saveRecordingLocally(recordingId, blob);
      await clearAudioChunks(recordingId);
      setRecording(false);
    };

    recorder.start(CHUNK_INTERVAL_MS); // timeslice = 3s chunks
    setRecording(true, recordingId);
    mediaRecorderRef.current = recorder;
  };

  // ...stop, recovery logic
}
```

```typescript
// lib/audio/chunk-store.ts
import { openDB } from 'idb';

const DB_NAME = 'allure-audio';
const STORE_NAME = 'chunks';

async function getDB() {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      db.createObjectStore(STORE_NAME, { autoIncrement: true });
    },
  });
}

export async function saveAudioChunk(recordingId: string, chunk: Blob) {
  const db = await getDB();
  await db.add(STORE_NAME, { recordingId, chunk, timestamp: Date.now() });
}

export async function getAudioChunks(recordingId: string): Promise<Blob[]> {
  const db = await getDB();
  const all = await db.getAll(STORE_NAME);
  return all
    .filter((entry) => entry.recordingId === recordingId)
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((entry) => entry.chunk);
}

export async function clearAudioChunks(recordingId: string) {
  const db = await getDB();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);
  const all = await store.getAll();
  for (const entry of all) {
    if (entry.recordingId === recordingId) {
      // Need index or iterate with cursor for deletion
    }
  }
}
```

```typescript
// stores/recording-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface RecordingState {
  isRecording: boolean;
  currentRecordingId: string | null;
  startedAt: number | null; // Date.now() timestamp
  setRecording: (recording: boolean, id?: string) => void;
}

export const useRecordingStore = create<RecordingState>()(
  persist(
    (set) => ({
      isRecording: false,
      currentRecordingId: null,
      startedAt: null,
      setRecording: (recording, id) =>
        set({
          isRecording: recording,
          currentRecordingId: recording ? (id ?? null) : null,
          startedAt: recording ? Date.now() : null,
        }),
    }),
    { name: 'allure-recording' } // localStorage key
  )
);
```

### Pattern 2: Next.js API Route Proxy to FastAPI

**What:** Next.js route handlers forward requests to the Python FastAPI backend. For JSON requests, parse and re-send. For file uploads, stream the request body directly.

**When to use:** All backend communication.

**Example:**

```typescript
// app/api/recordings/route.ts
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// GET /api/recordings -> proxy to FastAPI
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${BACKEND_URL}/recordings${searchParams ? `?${searchParams}` : ''}`;

  const response = await fetch(url);
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}

// POST /api/recordings -> proxy multipart upload to FastAPI
export async function POST(request: NextRequest) {
  const formData = await request.formData();

  const response = await fetch(`${BACKEND_URL}/recordings`, {
    method: 'POST',
    body: formData, // Forward the FormData directly
    // Do NOT set Content-Type -- let fetch generate the boundary
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
```

**Critical note for file uploads:** Do NOT manually set the `Content-Type` header when forwarding `FormData`. The browser/Node.js fetch automatically generates the correct `multipart/form-data` boundary. Setting it manually corrupts the boundary and the upload will fail.

### Pattern 3: Status Polling with TanStack Query

**What:** Use `refetchInterval` as a function that returns an interval when processing, and `false` when complete.

**When to use:** After a recording is assigned and upload/transcription is in progress.

**Example:**

```typescript
// hooks/use-recordings.ts
import { useQuery } from '@tanstack/react-query';

export function useRecordingStatus(recordingId: string | null) {
  return useQuery({
    queryKey: ['recording-status', recordingId],
    queryFn: () => fetch(`/api/recordings/${recordingId}/status`).then(r => r.json()),
    enabled: !!recordingId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'complete' || status === 'error') {
        return false; // Stop polling
      }
      return 3000; // Poll every 3 seconds while processing
    },
  });
}
```

### Pattern 4: Local-First Recording Metadata with better-sqlite3

**What:** Use better-sqlite3 in Next.js API routes (server-side only) for recording metadata, project assignments, and status tracking. This is the local-first database that survives independently of the Python backend.

**When to use:** Recording list, project CRUD, status tracking before backend involvement.

**Example:**

```typescript
// lib/db/index.ts
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const DB_DIR = path.join(process.env.HOME || '~', '.allure');
const DB_PATH = path.join(DB_DIR, 'allure.db');

// Ensure directory exists
if (!fs.existsSync(DB_DIR)) {
  fs.mkdirSync(DB_DIR, { recursive: true });
}

const db = new Database(DB_PATH);

// Enable WAL mode for better concurrent read performance
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

export default db;
```

```sql
-- lib/db/schema.sql
CREATE TABLE IF NOT EXISTS recordings (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  duration_ms INTEGER DEFAULT 0,
  file_path TEXT,
  status TEXT NOT NULL DEFAULT 'unassigned',  -- unassigned | processing | ready | error
  project_id TEXT,
  backend_id TEXT,  -- ID from Python backend after upload
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Important:** better-sqlite3 is synchronous and uses native addons. It works in Next.js API routes and server components but NOT in client components or Edge runtime. The DB singleton pattern above works because Next.js API routes run in Node.js.

### Anti-Patterns to Avoid

- **Accumulating audio in memory:** Do NOT collect all MediaRecorder chunks in a JavaScript array and only save on stop. If the browser crashes, all audio is lost. Use `timeslice` + IndexedDB for progressive saving.
- **Setting Content-Type on FormData uploads:** Let the runtime set the multipart boundary automatically. Manual Content-Type headers corrupt uploads.
- **Using better-sqlite3 in client components:** It is a native Node.js addon. It cannot run in the browser. Use it only in API routes and server components.
- **Polling without a stop condition:** Always check the response status and disable `refetchInterval` when processing is complete. Unbounded polling wastes resources and can mask errors.
- **Using `'use client'` on the entire Recording Hub page:** The table data fetch can happen server-side. Only the interactive parts (tab switching, dropdown assignment, FAB) need client-side rendering. Use composition: server component fetches data, passes to client component for interactivity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IndexedDB access | Raw IndexedDB callbacks | `idb` library (^8.0) | IndexedDB API is callback-based, error-prone, and verbose. idb adds Promises and TypeScript types in 1.2KB |
| Audio chunk storage | Custom file-based persistence | IndexedDB via idb | Browser filesystem APIs are experimental and limited; IndexedDB handles Blobs natively and survives crashes |
| Table with sorting/filtering | Custom `<table>` with sort state | @tanstack/react-table | Sorting, filtering, and pagination logic is deceptively complex; TanStack Table is headless and Tailwind-compatible |
| Toast notifications | Custom notification system | Sonner | Stacking, auto-dismiss, promise toasts, and accessibility handled out of the box |
| Component variants | Custom className concatenation | shadcn/ui + cva | shadcn components handle variants, accessibility, and keyboard navigation |
| UUID generation | Custom ID generator | `crypto.randomUUID()` | Built into all modern browsers and Node.js; cryptographically secure |

**Key insight:** Phase 1 has zero novel UI challenges. Every component (table, tabs, dropdown, badge, button, dialog) is covered by shadcn/ui. The novel parts are the audio recording pipeline and the proxy integration, which are logic problems, not UI problems.

## Common Pitfalls

### Pitfall 1: MediaRecorder MIME Type Mismatch with Whisper

**What goes wrong:** MediaRecorder produces `audio/webm;codecs=opus` but Whisper expects WAV/MP3/FLAC input. The file uploads successfully but transcription fails or produces garbage.
**Why it happens:** Developers test recording in isolation without testing the full pipeline to Whisper.
**How to avoid:** The Python backend must transcode WebM/Opus to 16kHz mono WAV using ffmpeg before feeding to Whisper. Verify ffmpeg is installed on the backend. Test the full pipeline (record -> upload -> transcode -> transcribe) on day 1.
**Warning signs:** Whisper returns empty transcript or errors on uploaded files.

### Pitfall 2: FormData Proxy Boundary Corruption

**What goes wrong:** Next.js route handler manually sets `Content-Type: multipart/form-data` when proxying to FastAPI. This omits the boundary parameter, making the upload unparseable.
**Why it happens:** Developers copy patterns from JSON API calls where Content-Type is set explicitly.
**How to avoid:** Never set Content-Type when sending FormData. Let fetch generate it automatically with the correct boundary.
**Warning signs:** FastAPI returns 422 Unprocessable Entity or "missing boundary" errors.

### Pitfall 3: better-sqlite3 in Client Components

**What goes wrong:** Importing better-sqlite3 in a `'use client'` component causes a build error: "Module not found: Can't resolve 'better_sqlite3.node'" or similar native addon errors.
**Why it happens:** better-sqlite3 is a native C++ addon that only runs in Node.js. Webpack/Turbopack cannot bundle it for the browser.
**How to avoid:** Only use better-sqlite3 in: (1) `app/api/` route handlers, (2) Server Components that never become client-rendered, (3) Server Actions. For client components, fetch data via API routes that internally use better-sqlite3.
**Warning signs:** Build errors mentioning native addons or .node files.

### Pitfall 4: Recording State Lost on Navigation

**What goes wrong:** User starts recording, navigates to another page, and the MediaRecorder is garbage-collected because the React component that created it unmounted.
**Why it happens:** MediaRecorder is tied to the component lifecycle. If the component unmounts, the recorder reference is lost.
**How to avoid:** The recording logic must be lifted outside of component lifecycle. Options: (1) Store the MediaRecorder instance in a module-level variable (outside React), (2) Use a Zustand store with a non-serializable `mediaRecorder` ref (using `skipHydration`), (3) Use a global ref in the layout component that never unmounts. The FAB lives in the root layout, which never unmounts during navigation -- this is the simplest solution.
**Warning signs:** Recording stops or produces truncated audio after page navigation.

### Pitfall 5: IndexedDB Storage Quota

**What goes wrong:** After several long recordings stored in IndexedDB, the browser prompts the user for storage permission or silently fails to store new chunks.
**Why it happens:** Browsers have storage quotas. Chrome allows up to 80% of disk space in "best effort" mode but can evict data. Without persistent storage, IndexedDB data is considered temporary.
**How to avoid:** After a recording is completed and saved to the filesystem (via backend upload or local save), immediately clear its chunks from IndexedDB. IndexedDB is a temporary crash-recovery buffer, not long-term storage. For the FYP demo, this is unlikely to be an issue with short recordings.
**Warning signs:** `QuotaExceededError` in console, or `ondataavailable` callbacks silently failing.

### Pitfall 6: Polling Overload with Multiple Processing Recordings

**What goes wrong:** If multiple recordings are assigned simultaneously, each creates its own polling interval, hammering the backend with status requests.
**Why it happens:** Naive implementation creates one `useQuery` per recording with `refetchInterval`.
**How to avoid:** For the FYP (single user, sequential processing), this is unlikely. If it occurs, use a single query that fetches all processing recordings' statuses in one request (batch status endpoint), or only poll for the most recently assigned recording.
**Warning signs:** Network tab shows dozens of status requests per second.

## Code Examples

### Recording FAB Component

```typescript
// components/recording/recording-fab.tsx
'use client';

import { useRecordingStore } from '@/stores/recording-store';
import { useAudioRecorder } from '@/hooks/use-audio-recorder';
import { cn } from '@/lib/utils';
import { Mic, Square } from 'lucide-react';
import { useEffect, useState } from 'react';

export function RecordingFAB() {
  const { isRecording, startedAt } = useRecordingStore();
  const { startRecording, stopRecording } = useAudioRecorder();
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isRecording || !startedAt) {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isRecording, startedAt]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <button
      onClick={isRecording ? stopRecording : startRecording}
      className={cn(
        'fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full px-4 py-3 shadow-lg transition-all',
        isRecording
          ? 'bg-red-500 text-white animate-pulse'
          : 'bg-primary text-primary-foreground hover:bg-primary/90'
      )}
    >
      {isRecording ? (
        <>
          <Square className="h-5 w-5 fill-current" />
          <span className="text-sm font-medium">{formatTime(elapsed)}</span>
        </>
      ) : (
        <Mic className="h-5 w-5" />
      )}
    </button>
  );
}
```

### Transcript Chat Bubbles

```typescript
// components/transcript/utterance-bubble.tsx
'use client';

import { cn } from '@/lib/utils';

interface Utterance {
  id: string;
  speaker: string;
  text: string;
  start_time: number; // seconds
  end_time: number;
}

// Distinct colors per speaker (Claude's discretion)
const SPEAKER_COLORS: Record<number, { bg: string; label: string }> = {
  0: { bg: 'bg-blue-50', label: 'text-blue-700' },
  1: { bg: 'bg-emerald-50', label: 'text-emerald-700' },
  2: { bg: 'bg-purple-50', label: 'text-purple-700' },
  3: { bg: 'bg-amber-50', label: 'text-amber-700' },
  4: { bg: 'bg-rose-50', label: 'text-rose-700' },
};

function getSpeakerIndex(speaker: string): number {
  // Extract number from "Speaker 1", "Speaker 2", etc.
  const match = speaker.match(/\d+/);
  return match ? (parseInt(match[0]) - 1) % 5 : 0;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function UtteranceBubble({ utterance }: { utterance: Utterance }) {
  const idx = getSpeakerIndex(utterance.speaker);
  const colors = SPEAKER_COLORS[idx] ?? SPEAKER_COLORS[0];

  return (
    <div className={cn('rounded-lg px-4 py-3 max-w-[85%]', colors.bg)}>
      <div className="flex items-center gap-2 mb-1">
        <span className={cn('text-xs font-semibold', colors.label)}>
          {utterance.speaker}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatTimestamp(utterance.start_time)}
        </span>
      </div>
      <p className="text-sm text-foreground">{utterance.text}</p>
    </div>
  );
}
```

### Auto-Generated Recording Title (Claude's Discretion)

```typescript
// lib/utils.ts
import { format } from 'date-fns';

export function generateRecordingTitle(date: Date = new Date()): string {
  // "Recording - Mar 12, 2:35 PM"
  return `Recording - ${format(date, 'MMM d, h:mm a')}`;
}
```

### Polling Interval Strategy (Claude's Discretion)

Recommended: 3-second interval during processing, with automatic stop on completion or error. No exponential backoff needed for FYP scale (single user, single recording at a time). If processing typically takes 30-120 seconds, 3-second polling produces 10-40 requests -- entirely acceptable.

```typescript
refetchInterval: (query) => {
  const status = query.state.data?.status;
  if (!status || status === 'complete' || status === 'error') return false;
  return 3000;
},
```

### Error State Patterns (Claude's Discretion)

```typescript
// Three error states to handle:
// 1. Upload failure -> toast with retry option, status remains "unassigned"
// 2. Transcription failure -> status set to "error", detail page shows error message
// 3. Microphone permission denied -> toast with instructions to enable mic

// Use Sonner for all toast notifications:
import { toast } from 'sonner';

// Upload failure
toast.error('Upload failed', {
  description: 'Could not send recording to server. Check your connection.',
  action: { label: 'Retry', onClick: () => retryUpload(recordingId) },
});

// Transcription failure
toast.error('Transcription failed', {
  description: 'The backend encountered an error processing this recording.',
});

// Mic permission denied
toast.error('Microphone access denied', {
  description: 'Enable microphone access in your browser settings to record.',
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `navigator.getUserMedia()` (deprecated) | `navigator.mediaDevices.getUserMedia()` | 2017+ | Use the mediaDevices version; old one removed from some browsers |
| Accumulate chunks in memory array | `timeslice` + IndexedDB persistence | Best practice | Enables crash recovery (REC-03) |
| Next.js middleware for API proxy | Route handlers in `app/api/` | Next.js 13+ (App Router) | Route handlers are the correct pattern; middleware/proxy.js is for request interception, not API proxying |
| `useEffect` + `useState` for data fetching | TanStack Query | 2022+ | Eliminates manual loading/error/caching state management |
| Redux for all state | Zustand (client) + TanStack Query (server) | 2023+ | Clean separation of client UI state and server data |

**Note on Next.js 16:** Next.js 16 renames `middleware.ts` to `proxy.ts`. This project targets Next.js 15 where `middleware.ts` is still the convention. This does not affect API route handlers in `app/api/` which are the actual proxy mechanism for FastAPI communication.

## Open Questions

1. **Backend API contract**
   - What we know: FastAPI backend exists at `github.com/ZainAbbas97/allure-ai` with Whisper STT pipeline
   - What's unclear: Exact endpoint URLs, request/response shapes, status enum values, whether diarization is already implemented
   - Recommendation: Read the actual FastAPI route definitions on day 1 before building any frontend API calls. The assumed contract shape from ARCHITECTURE.md may not match reality.

2. **Audio file storage path**
   - What we know: Decision says `~/.allure/recordings/` for audio files
   - What's unclear: Does the Python backend expect to receive files and store them itself, or should the Next.js frontend save to filesystem and pass the path?
   - Recommendation: The backend should handle file storage. Frontend uploads via multipart/form-data, backend saves to `~/.allure/recordings/`.

3. **better-sqlite3 vs backend SQLite**
   - What we know: Both frontend (better-sqlite3) and backend (Python sqlite3) use SQLite
   - What's unclear: Are they the same database file or separate? If same, concurrent access from Node.js and Python will cause locking issues.
   - Recommendation: Use separate database files. Frontend DB (`~/.allure/allure-frontend.db`) for local metadata (recording list, UI state). Backend DB for transcripts, outcomes, tasks. They communicate via REST API, not shared DB.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest ^3.0 + React Testing Library ^16.0 |
| Config file | None -- Wave 0 must create `vitest.config.ts` |
| Quick run command | `npx vitest run --reporter=verbose` |
| Full suite command | `npx vitest run` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REC-01 | FAB renders on all pages, click starts recording | integration | `npx vitest run src/components/recording/__tests__/recording-fab.test.tsx -t "start recording"` | Wave 0 |
| REC-02 | MediaRecorder captures audio with correct MIME type | unit | `npx vitest run src/hooks/__tests__/use-audio-recorder.test.ts -t "captures audio"` | Wave 0 |
| REC-03 | Audio chunks saved to IndexedDB, recoverable after simulated crash | unit | `npx vitest run src/lib/audio/__tests__/chunk-store.test.ts` | Wave 0 |
| REC-04 | Recording Hub displays recordings with correct status | integration | `npx vitest run src/components/recording/__tests__/recording-hub.test.tsx` | Wave 0 |
| REC-05 | Assigning project triggers upload | integration | `npx vitest run src/components/recording/__tests__/project-assignment.test.tsx` | Wave 0 |
| REC-06 | Unassigned recordings not sent to backend | unit | `npx vitest run src/hooks/__tests__/use-recordings.test.ts -t "unassigned"` | Wave 0 |
| STT-01 | API route proxies upload to FastAPI | unit | `npx vitest run src/app/api/recordings/__tests__/route.test.ts` | Wave 0 |
| STT-02 | Transcript displays timestamps | integration | `npx vitest run src/components/transcript/__tests__/transcript-view.test.tsx -t "timestamps"` | Wave 0 |
| STT-03 | Transcript displays speaker labels with colors | integration | `npx vitest run src/components/transcript/__tests__/utterance-bubble.test.tsx` | Wave 0 |
| STT-04 | Polling stops when status is complete | unit | `npx vitest run src/hooks/__tests__/use-recordings.test.ts -t "polling"` | Wave 0 |

### Sampling Rate

- **Per task commit:** `npx vitest run --reporter=verbose` (quick run, all tests)
- **Per wave merge:** `npx vitest run` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `vitest.config.ts` -- Vitest configuration with jsdom/happy-dom environment
- [ ] `src/test/setup.ts` -- Test setup file (MSW handlers for API mocking, IndexedDB mock)
- [ ] Framework install: `npm install -D vitest @testing-library/react @testing-library/jest-dom @vitejs/plugin-react happy-dom msw fake-indexeddb`
- [ ] `fake-indexeddb` needed for testing IndexedDB operations (chunk-store.test.ts)
- [ ] MSW (Mock Service Worker) for mocking API route responses in tests

## Sources

### Primary (HIGH confidence)
- [MDN MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder) -- MIME types, timeslice, ondataavailable
- [MDN MediaRecorder dataavailable event](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder/dataavailable_event) -- Chunk behavior with timeslice
- [better-sqlite3 npm](https://www.npmjs.com/package/better-sqlite3) -- v12.4.1, synchronous API, native addon constraints
- [better-sqlite3 API docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/api.md) -- Database class, pragma, prepare
- [Next.js Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers) -- App Router API routes
- [Next.js proxy.js (v16) / middleware.ts (v15)](https://nextjs.org/docs/app/api-reference/file-conventions/proxy) -- Confirmed middleware is for request interception, NOT API proxying
- [TanStack Query useQuery](https://tanstack.com/query/v5/docs/framework/react/reference/useQuery) -- refetchInterval as function
- [Zustand persist middleware](https://zustand.docs.pmnd.rs/reference/middlewares/persist) -- localStorage persistence for crash recovery
- [idb library](https://github.com/jakearchibald/idb) -- Promise-based IndexedDB wrapper

### Secondary (MEDIUM confidence)
- [Addpipe blog on MediaRecorder chunks](https://blog.addpipe.com/dealing-with-huge-mediarecorder-slices/) -- Chunk size variability with timeslice
- [Next.js proxy API patterns](https://www.nextsaaspilot.com/blogs/nextjs-proxy-api-route) -- Route handler proxy to external backend
- [GitHub Discussion: Next.js multipart form upload](https://github.com/vercel/next.js/discussions/39957) -- FormData proxying, boundary handling

### Tertiary (LOW confidence)
- [AudioStore IndexedDB streaming](https://github.com/kevincennis/AudioStore) -- Concept validation for IndexedDB audio storage (older project)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified against npm registry and official docs
- Architecture: HIGH -- patterns are well-established (MediaRecorder, IndexedDB, route handlers, polling)
- Pitfalls: HIGH -- based on verified browser API behavior and known Next.js constraints
- Crash recovery: MEDIUM -- the IndexedDB + Zustand persist pattern is sound but untested at scale; chunk reassembly needs validation with actual WebM/Opus files
- Backend integration: LOW -- actual FastAPI endpoint contracts not yet verified against real backend code

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain, 30-day validity)

