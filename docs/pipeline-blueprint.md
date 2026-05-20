# Allure Pipeline Blueprint

A handoff document. Read this and you should be able to reproduce the audio→transcript→outcomes pipeline in a fresh codebase. The intent is to describe *what each piece does, why, and the gotchas* — not to dump a spec.

The system has two halves that talk over SQLite:
- **Backend**: Python FastAPI app that owns the heavy ML work (STT, diarization, LLM extraction).
- **Frontend**: Next.js app that owns the user-facing UI and a local SQLite for recordings/projects/tasks/etc.

A recording exists in **both** DBs (the backend has a `jobs` row keyed by `backend_id`, the frontend has a `recordings` row keyed by its own `id` and storing `backend_id` as a foreign-key-ish pointer). The two stay in sync via direct cross-process writes — see "The consistency contract" below.

---

## 1. Folder layout

```
allure-ai-web/
├── backend/                         # Python (FastAPI, asyncio queues)
│   ├── main.py                      # FastAPI app, lifespan, all routes
│   ├── job_queue.py                 # asyncio worker for stt/extract/finalize
│   ├── transcription.py             # FastDiarizer + run_transcription
│   ├── extraction.py                # Phi-4-mini extraction + fallback helpers
│   ├── text_post.py                 # punctuation + capitalization restore
│   ├── frontend_sync.py             # cross-process writes to frontend SQLite
│   ├── observability.py             # step_timer + log_event
│   ├── storage.py                   # SQLite layer (jobs, attachments, etc.)
│   ├── audio_utils.py               # ffmpeg conversion, format detection
│   ├── models.py                    # Pydantic request/response models
│   ├── meeting_bot/                 # Google-Meet bot integration
│   │   ├── router.py                # /meeting-bot/* endpoints
│   │   ├── watcher.py               # polls bot recording dir
│   │   ├── forwarder.py             # POSTs finished recordings to /recordings
│   │   └── dispatch_store.py        # dispatch lifecycle in SQLite
│   ├── data/allure.db               # backend SQLite (gitignored)
│   ├── uploads/                     # WAV files keyed by job id (gitignored)
│   └── tests/                       # pytest
├── src/                             # Next.js (App Router, React Query)
│   ├── app/
│   │   ├── (dashboard)/recordings/[id]/page.tsx    # recording detail
│   │   ├── api/recordings/[id]/
│   │   │   ├── route.ts             # GET/PATCH/DELETE (PATCH locks title_is_auto)
│   │   │   ├── status/route.ts      # poll target — also pre-fetches transcript
│   │   │   ├── transcript/route.ts  # caches transcript locally
│   │   │   ├── outcomes/route.ts    # proxies + persists outcomes locally
│   │   │   ├── reprocess/route.ts   # re-queue full pipeline
│   │   │   └── extract/route.ts     # manual extract trigger
│   │   └── api/recordings/route.ts  # upload + list
│   ├── hooks/
│   │   ├── use-recordings.ts        # useRecording, useRecordingStatus,
│   │   │                            # useReprocessRecording, useDeleteRecording
│   │   └── use-outcomes.ts          # useOutcomes, useExtractionStatus
│   ├── lib/db/
│   │   ├── index.ts                 # singleton + ALTER TABLE migrations
│   │   ├── recordings.ts            # recordings/transcript_data CRUD
│   │   ├── outcomes.ts              # outcomes upsert
│   │   └── schema.sql               # CREATE TABLE IF NOT EXISTS for everything
│   ├── components/
│   │   ├── transcript/              # transcript view + speaker stats
│   │   ├── outcome/                 # outcomes panel
│   │   └── recording/               # status badge, stat cards
│   └── types/recording.ts           # Recording, Transcript, SpeakerStat types
└── public/recordings/allure-frontend.db   # frontend SQLite (gitignored)
```

The backend can open the frontend SQLite directly — both are local files on the same disk. That's how cross-process writes work without a network hop.

---

## 2. Models loaded at startup (`backend/main.py:lifespan`)

| Model | Purpose | Why this one |
|---|---|---|
| `moonshine-voice` (small) | STT | Lightweight CPU STT. Outputs unpunctuated, all-lowercase text. Faster than Whisper-tiny at ~equal accuracy on clean audio. |
| `silero-vad` | Voice activity detection | ~1.8 MB ONNX. Speech-only embedding extraction is the single most load-bearing piece of the diarizer. |
| `speechbrain/spkrec-ecapa-voxceleb` | Speaker embeddings (ECAPA-TDNN) | 192-dim embeddings, robust to short windows when fed only speech. |
| `oliverguhr/fullstop-punctuation-multilang-large` | Punctuation restoration | Loaded via `deepmultilingualpunctuation`. Patches the old `grouped_entities=False` API to use modern `aggregation_strategy="none"`. |
| `unsloth/Phi-4-mini-instruct-GGUF` (Q4_K_M) | LLM extraction | 3.8B params, runs on CPU via `llama-cpp-python`. Used for outcomes + title + description + transcript corrections in a single JSON-schema-constrained call. |

The lifespan also runs three idempotent startup tasks:
1. `_migrate_speaker_stats()` — recomputes extended speaker stats for legacy jobs.
2. `_backfill_meeting_metadata()` — synthesizes title/description from transcript segments where the LLM returned empty.
3. `_sync_all_metadata_to_frontend()` — pushes every completed backend job's title/description into the frontend SQLite. Catches anything the live push missed.

---

## 3. The pipeline (`backend/transcription.py:run_transcription`)

This is the heavy work that runs in the `job.stt` worker.

```
audio (.wav, 16 kHz mono)
  → librosa.load
  → step "stt.moonshine"        Moonshine STT → [{start, end, text, confidence}]
  → step "diarization"          FastDiarizer.diarize(wav_path) → speaker segments
  → step "align"                align_transcript_with_speakers (max-overlap + nearest fallback)
  →                             punctuate_segments(segments, punctuator) — restores . , ? ! and capitalization
  → step "merge"                merge consecutive same-speaker segments
  → step "stats"                calculate_speaker_stats — talk_time_pct, wpm, pauses, turns
  → step "speaker_id.llm"       identify_speakers_with_llm (Phi-4-mini, names+roles)
  → return dict                 {id, duration, language, speakers, segments, processing_time}
```

Each step is wrapped in `step_timer(...)` from `observability.py` so timing surfaces as structured logs (and feeds into the planned Logs UI).

### The diarizer (`FastDiarizer` class)

See `DIARIZATION.md` (separate file, gitignored, local notes) for the long-form decision journal. Short version:

| Component | What it does | Tunable env var |
|---|---|---|
| silero-vad | speech-only intervals | `DIARIZER_VAD_THRESHOLD`, `DIARIZER_MIN_SPEECH_SECONDS` |
| ECAPA-TDNN windows | 2s window, 0.75s hop on speech intervals only | `DIARIZER_WINDOW_SECONDS`, `DIARIZER_HOP_SECONDS` |
| RMS-normalize chunks | neutralizes browser AGC drift | (inline) |
| L2-normalize embeddings | stable cosine distances | (inline) |
| **NME-SC spectral clustering** | builds top-p sparsified affinity matrix, picks K from eigengap of normalized Laplacian | `DIARIZER_CLUSTERING_METHOD` |
| **Skip gap[0]** | the Fiedler value is always ~0, so `argmax(gaps[1:]) + 2` is the right K selector | (hardcoded) |
| Centroid-merge safety net | merges clusters whose centroids are closer than threshold; disabled by default (`0.0`) | `DIARIZER_CENTROID_MERGE_THRESHOLD` |
| Cap max speakers | hard ceiling on K | `DIARIZER_MAX_SPEAKERS` (default 6) |
| Hop-proportional median filter | smooths label flicker; size scales with hop | (inline) |
| Non-overlapping segment emission | midpoint boundaries between overlapping windows | (inline) |

**Critical decision: no mean-centering.** An L2 → mean-center → L2 step was tried as "channel adaptation". For low-K recordings the mean lands between the speakers and centering destroys speaker separability. Removed; spectral + affinity sparsification absorbs channel variation.

**Critical decision: centroid_merge_threshold defaults to 0.0.** I had it at 0.80 for a while based on one calibration recording. Real 2-speaker centroids land at 0.6–0.75, so any non-zero threshold ate legitimate K=2 detections. Disabled by default; under-detection is the user complaint, over-detection on mono recordings is rare and fixable in the UI.

### Punctuation step (`text_post.py:punctuate_segments`)

Per-segment because Moonshine already segments on silence (≈sentence-shaped). Concatenating across segments would risk losing the boundaries the diarizer relies on.

Wrapper patches the upstream `deepmultilingualpunctuation` library at import time — it was written against a transformers version that used `grouped_entities=False`, which was removed in transformers ≥5. We monkey-patch `__init__` to use `aggregation_strategy="none"` instead.

Capitalization is a regex post-pass (not from the model): capitalize segment start, capitalize after `.?!`, and standalone `i` → `I`. The punctuation model produces no casing on its own.

### Extraction step (`extraction.py:run_extraction`)

One Phi-4-mini call with a JSON-schema-constrained response. The schema requires:

```jsonc
{
  "meeting_title":       "5–8 words, title case",
  "meeting_description": "1–2 sentences",
  "outcomes":            [...decision / action_item / requirement / blocker...],
  "transcript_corrections": [   // optional, gated by EXTRACTION_WORD_CORRECTIONS=1
    {"segment_index": int, "original_text": str, "corrected_text": str,
     "confidence": float, "reason": "≤12 words"}
  ]
}
```

Why one call: the transcript is the most expensive part of the prefill, and we'd otherwise pay it three times (outcomes, naming, corrections). Bundling adds maybe 300 output tokens to an already-running call.

**Always-non-empty title.** Phi-4-mini sometimes satisfies "required string" with `""` on short or low-content recordings. We have `_fallback_title_from_segments(segments)` that produces a deterministic 5–8 word title from the longest early segment — never returns empty. Same idea for `_fallback_description_from_segments`. Applied as a post-parse fallback, not via re-prompting.

**Word corrections are gated and conservative.** Each correction must include a `reason` field, the model's `original_text` must loosely match the actual segment (case-insensitive substring), and `confidence >= 0.85` to apply. We never re-write segments without all three guards.

---

## 4. Job queue (`backend/job_queue.py`)

Two queues:

- **`job_queue`** — sequential single worker. Processes `stt`, `extract`, `finalize` jobs. Sequential because they all hit the local Llama lock and the heavy models.
- **`chunk_queue`** — concurrent worker pool (default 2, `STT_CHUNK_CONCURRENCY` env var). Processes streaming `stt_chunk` jobs. CPU-bound shared models are inference-only and thread-safe.

### The two race conditions and how they were fixed

These both bit us. Document them so they don't get re-introduced.

**Race A — STT→extract gap.** Old code:
```python
update_job(job_id, status="completed", result=result)   # write 1
update_job(job_id, extraction_status="pending")          # write 2
```
A frontend poll landing between writes 1 and 2 sees `status=ready + extraction_status="none"`. The polling hook treated "none" as a settled state and *stopped polling*. The title sync trigger then never fired.

**Fix**: atomic single write.
```python
update_job(job_id, status="completed", result=result, extraction_status="pending")
```

**Race B — Extract completion ordering.** Old code flipped `extraction_status="completed"` before pushing title/description to the frontend SQLite. Frontend would see "completed", invalidate React Query caches, refetch — but the local DB still had the placeholder title.

**Fix**: in the extract job, do these in this order:
1. Write `result` (with title/description) into backend `jobs` row.
2. `push_metadata_to_frontend(...)` — write title/description into the frontend recordings row, NULL out the cached transcript blob.
3. `rename_audio_files(...)` — rename the WAV/webm on disk and update `file_path` in both DBs.
4. *Then* `update_job(extraction_status="completed", outcomes=outcomes)` — this is the signal the frontend hook reacts to, so the frontend DB must already be consistent before this flip.

---

## 5. The consistency contract

This is the key insight that took us a long detour to discover.

**Don't rely on the frontend pulling data via polling.** The frontend's React Query state lives in the browser; React Query caches stick across renders; HMR doesn't refresh in-memory state; status routes fire-and-forget mean DB writes can lag behind invalidation triggers.

**Have the backend push.** When extraction completes, the backend opens the frontend's SQLite file (`public/recordings/allure-frontend.db`) directly and writes the new title/description into the recordings row whose `backend_id` matches. It also NULLs out `transcript_data` so the next page visit re-fetches a fresh transcript.

The polling hook on the frontend then just needs to invalidate `["recordings"]`, `["recording", id]`, `["transcript", id]` on `extraction_status === "completed"`. The data is already in the local DB; the invalidation just triggers a re-render.

### `backend/frontend_sync.py`

Two functions are the entire push API:

```python
def push_metadata_to_frontend(
    backend_job_id: str,
    title: str | None = None,
    description: str | None = None,
) -> dict:
    """Write title/description to recordings row matching backend_id.
    Respects title_is_auto (won't overwrite manual renames). Clears
    cached transcript blob. Never raises."""

def rename_audio_files(
    backend_job_id: str,
    title: str,
    backend_wav_path: str | None,
) -> dict[str, str | None]:
    """Slugify title, rename backend WAV and frontend webm to include
    the slug + short job id. Updates file_path in both DBs. Never raises."""
```

Filesystem-safe slug: `re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]`. Files become `<slug>-<short_id>.<ext>`, e.g. `language-and-comprehension-test-1bbc26eb.wav`.

The `title_is_auto` column on `recordings` is a flag. It starts at `1`. The PATCH `/api/recordings/[id]` endpoint sets it to `0` when the user submits a manual title (`hooks/use-recordings.ts:useRenameRecording`). The push respects this flag — manually-renamed titles stay. **Exception**: hitting "Reprocess" explicitly resets `title_is_auto=1` because the user is signaling "give me a fresh take".

---

## 6. Reprocess (manual re-run from existing audio)

Triggered from the recording detail page's "⋯" → Reprocess dropdown item.

Flow:
1. Frontend `useReprocessRecording` mutation → `POST /api/recordings/[id]/reprocess`.
2. Next.js proxy → `POST {BACKEND_URL}/recordings/{backend_id}/reprocess`.
3. Backend resets `status="pending"`, `result=None`, `outcomes=[]`, `extraction_status="none"`, then `await job_queue.put((job_id, "stt"))`. Audio file on disk is reused — the existing `file_path` is the source of truth.
4. Next.js proxy also flips local `status="processing"`, clears cached transcript, **resets `title_is_auto=true`** (so a manual rename gets overwritten by the new auto title).
5. `useReprocessRecording.onSuccess` invalidates `["recordings"]`, `["recording", id]`, `["transcript", id]`, `["recording-status", id]`, `["extraction-status", id]`, `["outcomes", id]`. All polling resumes, the page re-flows to its loading state, and when the pipeline completes the new title arrives via the same push mechanism.

---

## 7. Database schemas

### Backend `data/allure.db`

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,                           -- UUID, this is the public "recording id" for the backend
    file_path TEXT NOT NULL,                       -- absolute path to the .wav
    original_filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',        -- pending | processing | completed | failed
    result TEXT,                                   -- JSON: full transcript+stats+title+description+corrections
    error TEXT,
    extraction_status TEXT NOT NULL DEFAULT 'none',-- none | pending | processing | completed | failed
    extraction_error TEXT,
    outcomes TEXT NOT NULL DEFAULT '[]'            -- JSON array of outcome dicts
);

CREATE TABLE attachments (id, recording_id, filename, file_type, file_size, extracted_text, ...);
CREATE TABLE dispatches (...);                     -- meeting_bot lifecycle
```

JSON columns are deserialized in `_row_to_dict` (`backend/storage.py`).

### Frontend `public/recordings/allure-frontend.db`

```sql
CREATE TABLE recordings (
    id TEXT PRIMARY KEY,                           -- local UUID
    title TEXT NOT NULL,
    description TEXT,                              -- ADDED by migration
    title_is_auto INTEGER NOT NULL DEFAULT 1,      -- ADDED by migration (1=auto, 0=user-set)
    duration_ms INTEGER,
    file_path TEXT,                                -- absolute path to local webm copy
    status TEXT NOT NULL DEFAULT 'unassigned',     -- unassigned | processing | ready | error
    project_id TEXT,
    backend_id TEXT,                               -- FK-ish to backend jobs.id
    error_message TEXT,
    transcript_data TEXT,                          -- ADDED by migration: cached transcript JSON blob
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE outcomes (id, recording_id, type, title, detail, confidence, evidence_refs, promoted, promoted_id);
CREATE TABLE projects (...);
CREATE TABLE tasks (id, ..., priority, due_date, assignee, tags);   -- columns ADDED by migration
CREATE TABLE requirement_records (...);
CREATE TABLE documents (...);
```

Migrations are an array in `src/lib/db/index.ts:createDatabase`. Adding a column: append `{ table, column, definition }` and it'll be added next time the DB opens (ALTER TABLE on first detection).

---

## 8. Env vars

All optional; defaults work. Setting any to a sentinel disables/overrides.

| Var | Default | Effect |
|---|---:|---|
| `DIARIZER_WINDOW_SECONDS` | `2.0` | ECAPA window length |
| `DIARIZER_HOP_SECONDS` | `0.75` | window stride |
| `DIARIZER_CLUSTERING_METHOD` | `spectral` | `agglomerative` for the fallback path |
| `DIARIZER_DISTANCE_THRESHOLD` | `0.75` | only used by agglomerative fallback |
| `DIARIZER_LINKAGE` | `average` | only used by agglomerative fallback |
| `DIARIZER_VAD_THRESHOLD` | `0.5` | silero-vad probability cutoff |
| `DIARIZER_MIN_SPEECH_SECONDS` | `0.5` | drop tiny VAD blips |
| `DIARIZER_CENTROID_MERGE_THRESHOLD` | `0.0` | disabled by default; see DIARIZATION.md |
| `DIARIZER_MAX_SPEAKERS` | `6` | hard ceiling on K |
| `DIARIZER_MIN_WINDOWS_FOR_SPECTRAL` | `10` | below this, fall back to agglomerative |
| `EXTRACTION_WORD_CORRECTIONS` | `1` | set `0` to drop transcript_corrections from the schema entirely |
| `EXTRACTION_WORD_CORRECTION_MIN_CONFIDENCE` | `0.85` | apply threshold for corrections |
| `PUNCTUATION_MODEL` | `oliverguhr/fullstop-punctuation-multilang-large` | swap to `-base` if you need faster |
| `LOG_LEVEL` | `INFO` | surfaces step timings to stdout |
| `STT_CHUNK_CONCURRENCY` | `2` | streaming chunk worker pool size |
| `LLM_GPU` | `1` | `0` to force CPU-only Phi-4-mini |
| `LLM_MODEL_PATH` | — | override Phi-4-mini GGUF path |
| `HF_TOKEN` | — | optional HuggingFace token for gated/private model downloads |
| `MEETING_BOT_URL` | `http://localhost:3001` | bot service |
| `MEETING_BOT_RECORDINGS_DIR` | `~/meeting-bot/recordings` | where the bot writes |
| `BACKEND_URL` (frontend-side) | `http://localhost:8000` | how Next.js reaches the backend |
| `FRONTEND_DB_PATH` (backend-side) | `<repo>/public/recordings/allure-frontend.db` | override for tests |

---

## 9. Endpoint reference

### Backend (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | ping |
| `POST` | `/recordings` | upload audio, create job, queue STT |
| `GET` | `/recordings/{id}/status` | `{status, extraction_status}` |
| `GET` | `/recordings/{id}/transcript` | full transcript JSON |
| `GET` | `/recordings/{id}/outcomes` | list of extracted outcomes |
| `POST` | `/recordings/{id}/extract` | manually trigger extraction (409 if already triggered) |
| `POST` | `/recordings/{id}/reprocess` | reset state and re-queue STT — see §6 |
| `POST` | `/recordings/{id}/outcomes/{index}/promote` | promote outcome → task/requirement |
| `POST` | `/recordings/{id}/generate-prd` | generate PRD document from transcript + attachments |
| `POST` | `/recordings/{id}/generate-diagram` | generate Mermaid diagram |
| `GET/POST/DELETE` | `/recordings/{id}/attachments[/{aid}]` | attachment CRUD |
| `GET` | `/recordings/{id}/audio` | stream audio file (206 partial content) |
| (plus a `/meeting-bot/*` router for dispatch lifecycle) | | |

### Next.js (proxy + local-DB-aware)

| Path | Behavior |
|---|---|
| `/api/recordings` POST | save local copy, create local row, forward to backend `/recordings` |
| `/api/recordings/[id]` GET/PATCH/DELETE | local DB CRUD; PATCH auto-flips `title_is_auto=0` on title change |
| `/api/recordings/[id]/status` | proxy + map status enum + prefetch transcript on transition + force-refresh when extraction completes |
| `/api/recordings/[id]/transcript` | cache-first via `transcript_data` blob; pulls from backend on miss; sync title/description if backend has fresher |
| `/api/recordings/[id]/outcomes` | proxy + upsert into local `outcomes` table |
| `/api/recordings/[id]/reprocess` | proxy + reset local state + clear cached transcript |
| `/api/recordings/[id]/extract` | proxy |
| `/api/recordings/[id]/audio` | proxy with range support |

---

## 10. React Query keys

Pick whatever convention you want, but be consistent across hooks because invalidations key off these:

```typescript
["recordings"]                              // list
["recording", id]                           // single
["recording-status", id]                    // poll
["extraction-status", id]                   // poll (could be merged with above)
["transcript", id]
["outcomes", id]
```

Invalidations on extraction-complete: invalidate `["recordings"]`, `["recording", id]`, `["transcript", id]`, and on the `useExtractionStatus` path also `["outcomes", id]`. Without invalidating `["recordings"]`, the meetings list stays stale.

Polling cadence: 3 seconds, stop when **both** `status` is `ready/error` AND `extraction_status` is `completed/failed`. **Do not** treat `"none"` as a settled extraction state (that's what allowed Race A above).

---

## 11. Dependencies

### Backend (`backend/requirements.txt`)
```
fastapi>=0.115
uvicorn[standard]>=0.34
python-multipart>=0.0.18
aiofiles>=24.1
pydantic>=2.0
python-dotenv>=1.0
moonshine-voice==0.0.49
speechbrain>=1.0
silero-vad>=5.1
deepmultilingualpunctuation>=1.0
scikit-learn>=1.5
librosa>=0.10
scipy>=1.12
numpy>=1.26
llama-cpp-python>=0.3.2
huggingface-hub>=0.25,<1.0
pdfplumber>=0.11
python-docx>=1.1
pytest>=8.0
pytest-asyncio>=0.24
httpx>=0.27
rapidfuzz>=3.10
sqlite-vec>=0.1.6
sentence-transformers>=3.0
anthropic>=0.40
openai>=1.50
cryptography>=43.0
```

### Frontend (`package.json`)
Next.js (App Router), React Query (`@tanstack/react-query`), `better-sqlite3` for the local DB, Tailwind + shadcn for UI, `lucide-react` for icons.

### System deps
`ffmpeg` (audio conversion), `libsndfile1` (librosa).

---

## 12. Observability (`backend/observability.py`)

Single helper used everywhere:

```python
@contextmanager
def step_timer(step: str, **fields):
    # logs step.start, step.done with dt_ms, or step.failed on exception
    # also writes a structured event row for the future Logs UI
```

Drop it around every meaningful pipeline stage. The cost is negligible and the resulting logs let you measure exactly where time is going:

```
step.start step=stt.moonshine job_id=abc duration_s=120.0
step.done  step=stt.moonshine dt_ms=18430 job_id=abc duration_s=120.0
step.start step=diarization job_id=abc
step.done  step=diarization dt_ms=4070  job_id=abc
step.start step=punctuate n_segments=36
step.done  step=punctuate  dt_ms=2284 n_segments=36
step.done  step=extraction.llm dt_ms=52153 job_id=abc n_segments=10 corrections_enabled=1
step.done  step=job.extract     dt_ms=52171 job_id=abc
```

Configure root logging at INFO level in `main.py` *before* importing app modules — uvicorn's default config swallows non-`uvicorn.*` loggers otherwise.

---

## 13. Lessons that cost real time

1. **VAD before short windows, not after.** Short ECAPA windows are great for turn-taking — but only if they're fed clean speech. Without VAD, short windows + silence chunks ⇒ exploding cluster count.

2. **Don't mean-center few-speaker embeddings.** The trick works for many-speaker recordings; for K∈{1,2,3} it actively destroys separability.

3. **Skip the trivial Fiedler gap in NME-SC.** The first eigenvalue of any connected graph's Laplacian is ~0, so gap[0] is always largest — picking K via `argmax(gaps)` collapses everything to K=1. Use `argmax(gaps[1:]) + 2`.

4. **A single magic-number centroid-merge threshold doesn't generalize.** 0.80 worked on one recording; ate real 2-speaker detections on others. Default to disabled, expose as env var.

5. **Cross-process state sync via DB beats polling-pull every time.** A `sqlite3.connect(other_apps_db.db); UPDATE; commit` is more reliable than coordinating React Query invalidations, status polling, and HMR.

6. **Atomic writes for paired state.** When two columns must be observed together (`status` and `extraction_status`), write them in one SQL `UPDATE`. Any code path that observes them through separate queries races otherwise.

7. **Always have a deterministic fallback for LLM-required fields.** Phi-4-mini happily returns `""` for required-string fields when the input is hard. Don't trust the schema — post-validate, and synthesize a non-empty value from existing data when the LLM produces nothing.

8. **Rename audio files with a slug** for human readability, but include a short ID suffix for filesystem uniqueness. Update file_path in *both* DBs so audio streaming endpoints still resolve.

9. **One LLM call > three calls** when they share input. The transcript is the expensive prefill; bundle title + description + corrections + outcomes into a single JSON-schema-constrained call.

10. **Auto vs manual title needs a flag.** `title_is_auto` decides whether the auto-pipeline overrides. Set to false on manual rename. Reset to true on explicit "Reprocess" (it's an opt-in for a fresh take).

---

## 14. To reproduce this from scratch

In order:

1. Build the **backend**:
   - FastAPI app skeleton, `lifespan` for model loading, SQLite jobs table (`backend/storage.py`), `audio_utils` for ffmpeg-to-wav, upload endpoint that writes to `uploads/` and calls `create_job`.
   - Add `job_queue.py` with the asyncio worker and a single `stt` job type — wire it up so upload enqueues an STT job and the worker calls `run_transcription`.
   - Implement `FastDiarizer` (`transcription.py`). Start with VAD → ECAPA windows → spectral clustering. Verify on a known 2-speaker recording — should output K=2.
   - Add `text_post.py` with the patched punctuation model. Hook it between alignment and remap-labels.
   - Add `extraction.py` with the Phi-4-mini call. JSON-schema with `meeting_title`, `meeting_description`, `outcomes`. Add the fallback helpers immediately — don't trust the schema's `required:`.
   - Add `extract` job type that chains after STT. The worker writes the result back via `update_job`.
   - Add `observability.step_timer` and wrap every step.

2. Build the **frontend**:
   - Next.js with React Query. SQLite via `better-sqlite3` with the migrations array pattern in `src/lib/db/index.ts`.
   - Upload page → POST `/api/recordings` (saves local copy, forwards to backend, creates local row).
   - Detail page → `useRecording` + `useRecordingStatus` + `useTranscript` + `useOutcomes`. Polling stops when both status and extraction settle.
   - Implement the transcript and outcomes proxy routes. Cache transcript blob in `recordings.transcript_data`.

3. Build the **cross-process sync** (`backend/frontend_sync.py`):
   - `push_metadata_to_frontend` opens the frontend SQLite, UPDATE the recordings row, NULL out `transcript_data`.
   - Wire it into the extract job worker: push *before* flipping `extraction_status=completed`.

4. Add **Reprocess**:
   - Backend endpoint that resets job state and re-queues STT.
   - Frontend proxy + mutation hook that invalidates all relevant query keys + resets `title_is_auto`.
   - UI button in the detail page dropdown.

5. Add **Reprocess UI**, **logs**, **rename audio**, and the **lifespan backfill helpers**. Keep iterating on diarization knobs as you encounter real recordings.

That's the path. The order matters — each step builds on the previous. Don't try to ship diarization and extraction in parallel; the schema decisions in extraction depend on the transcript shape diarization produces.
