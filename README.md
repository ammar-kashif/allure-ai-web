# Allure AI

Meeting intelligence platform that records meetings, transcribes audio with speaker diarization, extracts actionable insights, and generates product requirement documents — all powered by local ML models.

## Tech Stack

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Zustand, TanStack Query, SQLite |
| **Backend** | FastAPI, Python 3.11, SQLite, Moonshine Voice (STT), SpeechBrain (diarization), Phi-4-mini via llama-cpp (LLM) |
| **Infra** | Docker Compose, CPU-only PyTorch, ffmpeg |

## Features

- **Transcription** — Upload or record audio, get timestamped transcripts with speaker labels and confidence scores
- **Streaming / chunked uploads** — Long recordings are sliced client-side (IndexedDB-backed) and streamed to the backend chunk-worker for incremental transcription and crash-safe resume
- **Insight Extraction** — Automatically extract decisions, action items, requirements, and blockers via local LLM
- **Entity extraction** — Identify and link people, projects, and topics across meetings, with mention activity timelines
- **Projects** — Group recordings, outcomes, and documents under a project; archive when shipped
- **PRD Generation** — Generate structured product requirement documents with Mermaid diagrams from meeting outcomes and uploaded reference docs (PDF/DOCX)
- **Task Management** — Promote extracted outcomes to trackable tasks (kanban + list views)
- **Dashboard** — Aggregated stats across recordings, outcomes, tasks, and documents
- **Ghost (AI assistant)** — Project-scoped RAG assistant over your meeting corpus with citations, streaming answers, conversation history, cost tracking, and a built-in eval harness
- **Autonomy** — Detect actionable items from extraction output, execute approved auto-actions (e.g. promote-to-task), with per-run cost accounting and undo
- **Live meetings via bot (POC)** — Dispatch a Puppeteer-based bot to join Google Meet / Teams / Zoom and feed the recording straight into the pipeline. See [`docs/meeting-bot-poc.md`](docs/meeting-bot-poc.md).
- **Observability** — Structured event log, per-step timers, and a `/metrics` endpoint

## Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **ffmpeg** (backend audio processing)
- **Hugging Face token** (for downloading ML models) — get one at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

## Running Locally

### Frontend

```bash
npm install
npm run dev
# → http://localhost:3000
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` in the project root:

```
HF_TOKEN=<your-huggingface-token>
```

Start the server:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The frontend expects the backend at `http://localhost:8000`.

## Running with Docker

```bash
export HF_TOKEN=<your-huggingface-token>
docker compose up --build
```

This starts both services:
- **Frontend** — `http://localhost:3000`
- **Backend** — internal (port 8000, not exposed to host)

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_TOKEN` | Hugging Face API token for model downloads | *required* |
| `LLM_GPU` | GPU device ID (`0` = CPU) | `0` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `BACKEND_URL` | Backend URL (used by frontend in Docker) | `http://backend:8000` |

### Volumes

Docker Compose mounts three persistent volumes:

- `frontend-data` — stored audio recordings (`/app/public/recordings`)
- `backend-data` — SQLite database (`/app/data`)
- `backend-uploads` — uploaded attachments (`/app/uploads`)

## Scripts

```bash
npm run dev       # Next.js dev server
npm run build     # Production build (standalone)
npm run start     # Run production build
npm run test      # Vitest unit tests
npm run lint      # ESLint
```

## API Endpoints

Backend (FastAPI, port 8000). The Next.js layer proxies most of these under `/api/*` so the browser never talks to the backend directly.

**Recordings & pipeline**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/recordings` | Upload audio file (or open a streaming/chunked session) |
| `GET` | `/recordings/{id}/status` | Poll processing status |
| `GET` | `/recordings/{id}/transcript` | Transcript + speaker stats |
| `GET` | `/recordings/{id}/transcript/stream` | SSE stream of incremental segments |
| `GET` | `/recordings/{id}/audio` | Audio file (range-supported) |
| `POST` | `/recordings/{id}/extract` | Re-run outcome extraction |
| `POST` | `/recordings/{id}/reprocess` | Re-run full pipeline |
| `POST` | `/recordings/{id}/entitize` | Re-run entity extraction |
| `PATCH` | `/recordings/{id}/speakers/{label}` | Rename a diarized speaker |
| `DELETE` | `/recordings/{id}` | Delete recording |

**Outcomes, documents, attachments**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recordings/{id}/outcomes` | Extracted decisions / actions / requirements / blockers |
| `POST` | `/recordings/{id}/outcomes/{oid}/promote` | Promote outcome to task |
| `POST` | `/recordings/{id}/generate-prd` | Generate PRD document |
| `POST` | `/recordings/{id}/generate-diagram` | Generate Mermaid diagram |
| `POST` | `/recordings/{id}/attachments` | Upload reference document |
| `GET` | `/recordings/{id}/attachments` | List attachments |

**Projects & entities**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` `POST` | `/projects` | List / create projects |
| `GET` `PATCH` `POST` | `/projects/{id}` / `/archive` | Read, update, archive |
| `GET` | `/entities` / `/entities/{id}` / `/mentions` / `/activity` | Entities, mentions, activity timeline |

**Ghost (AI assistant)**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ghost/search` | RAG search across the corpus |
| `POST` | `/ghost/ask`, `/ghost/ask/stream` | Ask (sync or SSE stream) |
| `GET` `DELETE` | `/ghost/conversations[/{id}]` | Conversation history |
| `GET` `PATCH` | `/ghost/settings` | Provider, model, system prompt |
| `GET` | `/ghost/cost` | Per-conversation / total cost |
| `POST` `GET` | `/ghost/eval/*` | Generate eval set, run eval, fetch stats/runs |

**Autonomy**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recordings/{id}/autonomy` | Detected actions for a recording |
| `GET` `PATCH` | `/autonomy/settings` | Enable rules, thresholds |
| `GET` | `/autonomy/runs`, `/autonomy/cost` | Run history, cost |
| `POST` | `/autonomy/actions/{id}/undo`, `/autonomy/runs/{id}/undo` | Reverse an action / whole run |

**Meeting bot**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/meetings/dispatch` | Dispatch bot to a meeting URL |
| `GET` | `/meetings`, `/meetings/{id}` | List dispatches, get status |
| `POST` | `/meetings/{id}/stop` | Stop a bot |

**Ops**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health`, `/metrics`, `/logs` | Health, Prometheus-style metrics, event log |

## Project Structure

```
allure-ai/
├── src/
│   ├── app/
│   │   ├── (dashboard)/            # Dashboard, recordings, meetings, tasks,
│   │   │                           # documents, ghost, settings pages
│   │   └── api/                    # Next.js proxy routes → FastAPI
│   │       ├── recordings/  meetings/  tasks/  outcomes/
│   │       ├── projects/    documents/  logs/
│   │       ├── ghost/       (ask, ask-stream, conversations, cost, settings)
│   │       └── autonomy/    (runs, actions, settings, cost)
│   ├── components/
│   │   ├── audio/  recording/  transcript/  outcome/  task/
│   │   ├── document/  dashboard/  ghost/  autonomy/  ui/
│   ├── hooks/                      # use-recordings, use-bot-meeting,
│   │                               # use-autonomy, use-outcomes, …
│   ├── stores/                     # Zustand: playback, recording, bot-meeting,
│   │                               # evidence-highlight
│   ├── lib/
│   │   ├── api/client.ts           # Typed FastAPI client
│   │   ├── audio/                  # IndexedDB chunk store + recovery
│   │   └── db/                     # better-sqlite3 schema + repos
│   └── types/
├── backend/
│   ├── main.py                     # FastAPI app & route definitions
│   ├── job_queue.py                # Async worker pool + chunk-worker pool
│   ├── storage.py                  # SQLite CRUD (jobs, attachments)
│   ├── models.py                   # Pydantic schemas
│   ├── audio_utils.py              # Validation + ffmpeg conversion
│   ├── transcription.py            # Moonshine STT + SpeechBrain diarization
│   ├── extraction.py               # LLM outcome extraction
│   ├── text_extraction.py text_post.py  # PDF/DOCX extract + post-processing
│   ├── document_generation.py      # PRD + Mermaid generation
│   ├── projects_store.py segments_store.py  # Project & segment persistence
│   ├── frontend_sync.py            # Push state updates to UI
│   ├── observability.py log_store.py metrics.py  # Events, timers, metrics
│   ├── streaming/                  # chunk_worker, finalizer, progress, resume
│   ├── entities/                   # Entity extractor + store
│   ├── autonomy/                   # detector, executor, verifier, runner, store
│   ├── ghost/                      # RAG assistant: agent, retrieval/,
│   │                               # embeddings, llm, tools, triage, eval/
│   ├── meeting_bot/                # bot_client, router, watcher, dispatch_store
│   ├── data/  uploads/             # SQLite DB + uploaded files (volume-backed)
│   └── tests/                      # pytest suite
├── docs/                           # design.md, diarization.md,
│                                   # pipeline-blueprint.md, product.md,
│                                   # meeting-bot-poc.md, references/
├── bot-patches/                    # Patches applied to upstream meeting bot
├── ARCHITECTURE.md                 # System diagram + flow overview
├── docker-compose.yml
├── Dockerfile                      # Frontend (Next.js standalone)
└── backend/Dockerfile              # Backend (Python 3.11 + ffmpeg)
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system diagram and request flow.
