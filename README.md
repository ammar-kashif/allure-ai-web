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
- **Insight Extraction** — Automatically extract decisions, action items, requirements, and blockers via local LLM
- **PRD Generation** — Generate structured product requirement documents with Mermaid diagrams from meeting outcomes and uploaded reference docs (PDF/DOCX)
- **Task Management** — Promote extracted outcomes to trackable tasks
- **Dashboard** — Aggregated stats across recordings, outcomes, tasks, and documents

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/recordings` | Upload audio file |
| `GET` | `/recordings` | List all recordings |
| `GET` | `/recordings/{id}/status` | Poll processing status |
| `GET` | `/recordings/{id}/transcript` | Get transcript with speaker stats |
| `GET` | `/recordings/{id}/outcomes` | Get extracted insights |
| `POST` | `/recordings/{id}/outcomes/{oid}/promote` | Promote outcome to task |
| `POST` | `/recordings/{id}/documents/prd` | Generate PRD |
| `POST` | `/recordings/{id}/attachments` | Upload reference document |
| `GET` | `/recordings/{id}/attachments` | List attachments |
| `DELETE` | `/recordings/{id}` | Delete recording |

## Project Structure

```
allure-ai/
├── src/
│   ├── app/                  # Next.js App Router pages & API routes
│   ├── components/           # React components (audio, transcript, dashboard, etc.)
│   ├── hooks/                # Custom hooks (recordings, outcomes, documents, tasks)
│   ├── stores/               # Zustand state (playback, recording, highlights)
│   ├── lib/                  # API client, SQLite schema, utilities
│   └── types/                # TypeScript definitions
├── backend/
│   ├── main.py               # FastAPI app & endpoint definitions
│   ├── transcription.py      # Moonshine STT + SpeechBrain diarization
│   ├── extraction.py         # LLM-powered outcome extraction
│   ├── document_generation.py # PRD & Mermaid diagram generation
│   ├── storage.py            # SQLite CRUD operations
│   ├── models.py             # Pydantic schemas
│   ├── audio_utils.py        # Audio validation & conversion
│   ├── text_extraction.py    # PDF/DOCX text extraction
│   ├── job_queue.py          # Async background job processing
│   └── tests/                # pytest suite
├── docker-compose.yml
├── Dockerfile                # Frontend
└── backend/Dockerfile        # Backend
```

