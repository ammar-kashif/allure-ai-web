# Architecture

Allure AI is a two-tier app: a **Next.js 16 frontend** that owns UI + a thin proxy/persistence layer, and a **FastAPI Python backend** that owns the ML pipeline (transcription, diarization, extraction, RAG). Browser code never talks to the backend directly — every backend call is proxied through Next.js API routes so the backend can stay on an internal Docker network.

## Component diagram

```mermaid
graph TB
    subgraph Browser["Browser"]
        UI["Next.js Pages<br/>dashboard / recordings / meetings /<br/>tasks / documents / ghost / settings"]
        Hooks["React Query Hooks<br/>+ Zustand Stores"]
        IDB[("IndexedDB<br/>chunk store / recovery")]
        Recorder["MediaRecorder<br/>chunked upload"]
    end

    subgraph NextServer["Next.js Server (port 3000)"]
        APIProxy["/api/* route handlers<br/>(proxy + auth + validation)"]
        FrontDB[("better-sqlite3<br/>local cache / settings")]
    end

    subgraph FastAPI["FastAPI Backend (port 8000)"]
        Main["main.py<br/>routes + middleware"]
        JobQ["job_queue<br/>worker pool + chunk pool"]

        subgraph Pipeline["Audio pipeline"]
            AudioU["audio_utils<br/>ffmpeg / validate"]
            Stream["streaming/<br/>chunk_worker · finalizer · resume"]
            Trans["transcription<br/>Moonshine STT + SpeechBrain diarization"]
            Extract["extraction<br/>LLM outcomes"]
            Entities["entities/<br/>extractor + store"]
            DocGen["document_generation<br/>PRD + Mermaid"]
            TextX["text_extraction<br/>PDF / DOCX"]
        end

        subgraph Ghost["Ghost (RAG assistant)"]
            GAgent["agent · subagent · triage"]
            GRetrieve["retrieval/ + embeddings<br/>(sqlite-vec)"]
            GLLM["llm · tools"]
            GEval["eval/ (eval harness)"]
        end

        subgraph Autonomy["Autonomy"]
            ADetect["detector"]
            AExec["executor"]
            AVerify["verifier"]
            ARun["runner + store"]
        end

        subgraph MBot["Meeting bot"]
            MRouter["router"]
            MClient["bot_client (Puppeteer)"]
            MWatch["watcher · dispatch_store"]
            MFwd["forwarder"]
        end

        Obs["observability · log_store · metrics"]
        Storage["storage · projects_store ·<br/>segments_store · frontend_sync"]
        DB[("SQLite<br/>data/allure.db<br/>+ sqlite-vec")]
        Uploads[("uploads/ + recordings/")]
    end

    subgraph External["External / local models"]
        HF["Hugging Face Hub<br/>(model download)"]
        Phi["Phi-4-mini GGUF<br/>(llama-cpp-python)"]
        Anth["Anthropic / OpenAI<br/>(optional Ghost provider)"]
        Meet["Google Meet · Teams · Zoom"]
    end

    Recorder --> IDB
    IDB --> Hooks
    UI --> Hooks
    Hooks --> APIProxy
    APIProxy --> FrontDB
    APIProxy --> Main

    Main --> JobQ
    Main --> MRouter
    Main --> GAgent
    Main --> ARun
    Main --> Storage

    JobQ --> AudioU --> Trans --> Extract --> Entities
    JobQ --> Stream --> Trans
    Extract --> ADetect --> AExec --> AVerify
    AExec --> Storage
    Main --> DocGen
    DocGen --> TextX
    TextX --> Uploads

    GAgent --> GRetrieve --> DB
    GAgent --> GLLM
    GLLM --> Phi
    GLLM --> Anth
    GEval --> GAgent

    MRouter --> MClient --> Meet
    MClient --> MFwd --> Main
    MWatch --> Storage

    Pipeline --> Storage
    Storage --> DB
    Storage --> Uploads
    Trans --> HF
    Extract --> Phi
    Obs -.-> Main
    Obs -.-> Pipeline

    classDef store fill:#1e293b,stroke:#64748b,color:#e2e8f0
    classDef ext fill:#3b1f1f,stroke:#b45309,color:#fde68a
    class IDB,FrontDB,DB,Uploads store
    class HF,Phi,Anth,Meet ext
```

## Request flows

### 1. Upload → transcript → outcomes

```mermaid
sequenceDiagram
    participant U as Browser
    participant N as Next /api
    participant B as FastAPI
    participant Q as Job queue
    participant ML as Transcription + LLM
    participant S as SQLite

    U->>N: POST /api/recordings (audio)
    N->>B: POST /recordings
    B->>S: create job (status=queued)
    B-->>N: job_id
    N-->>U: job_id
    Q->>ML: convert → STT → diarize
    ML->>S: write segments + speakers
    Q->>ML: extract outcomes (LLM)
    ML->>S: write outcomes + entities
    loop poll / SSE
        U->>N: GET /recordings/{id}/transcript/stream
        N->>B: proxy SSE
        B-->>U: incremental segments
    end
```

### 2. Chunked / streaming upload (long recordings)

```mermaid
sequenceDiagram
    participant R as MediaRecorder
    participant IDB as IndexedDB
    participant N as Next /api
    participant CW as chunk_worker
    participant F as finalizer

    R->>IDB: append chunk
    IDB->>N: POST chunk N
    N->>CW: forward
    CW->>CW: transcribe chunk
    CW-->>N: partial segments (SSE)
    Note over R,F: on stop
    R->>N: POST finalize
    N->>F: stitch + diarize full audio
    F->>N: final transcript
```

### 3. Ghost (RAG) ask

```mermaid
sequenceDiagram
    participant U as Browser
    participant N as Next /api/ghost
    participant G as ghost.agent
    participant R as retrieval + embeddings
    participant L as LLM (Phi-4 or Anthropic/OpenAI)
    participant S as SQLite + sqlite-vec

    U->>N: POST /ghost/ask/stream
    N->>G: forward
    G->>R: embed query → vector search
    R->>S: top-k chunks (segments / docs)
    R-->>G: context + citations
    G->>L: prompt with context + tools
    L-->>G: tokens (stream)
    G-->>N: SSE answer + citations
    N-->>U: SSE
    G->>S: persist conversation + cost
```

### 4. Meeting bot

```mermaid
sequenceDiagram
    participant U as Browser
    participant N as Next /api/meetings
    participant R as meeting_bot.router
    participant BC as bot_client (Puppeteer)
    participant M as Google Meet/Teams/Zoom
    participant Fw as forwarder
    participant P as Pipeline

    U->>N: POST /meetings/dispatch {url}
    N->>R: dispatch
    R->>BC: launch headless browser
    BC->>M: join meeting + capture audio
    BC->>Fw: stream audio chunks
    Fw->>P: feed into chunk_worker
    P-->>U: live transcript (SSE)
    U->>N: POST /meetings/{id}/stop
    N->>R: stop → BC.disconnect
```

## Data stores

| Store | Owner | Purpose |
|---|---|---|
| `backend/data/allure.db` | FastAPI | Source of truth: jobs, segments, outcomes, entities, projects, ghost convos, autonomy runs. Uses `sqlite-vec` for embeddings. |
| `backend/uploads/` | FastAPI | Original audio + uploaded reference docs (PDF/DOCX). |
| `public/recordings/` | Next.js | Streamable audio served back to the browser. |
| `src/lib/db/*` (better-sqlite3) | Next.js server | Lightweight cache / local-only frontend state. |
| Browser IndexedDB | Browser | In-flight recording chunks for crash-safe resume. |

## External services

- **Hugging Face Hub** — one-time download of Moonshine STT, SpeechBrain diarization, and embedding models. Token via `HF_TOKEN`.
- **Local LLM** — Phi-4-mini GGUF via `llama-cpp-python` (CPU by default; `LLM_GPU` to switch).
- **Anthropic / OpenAI** (optional) — Ghost can be pointed at a hosted provider via `/ghost/settings`; keys live encrypted in the DB.
- **Meeting platforms** — Google Meet / Teams / Zoom joined via the Puppeteer-based meeting bot.

## Build & deploy

- **Frontend** (`Dockerfile`) — Node 20 Alpine, Next.js `output: 'standalone'`, ships with `better-sqlite3` native module and the `schema.sql` for runtime DB init.
- **Backend** (`backend/Dockerfile`) — Python 3.11 slim + ffmpeg + libsndfile. Installs CPU-only PyTorch first to skip the ~2.5 GB CUDA wheels, then builds `llama-cpp-python` with `GGML_CUDA=OFF`.
- **Compose** (`docker-compose.yml`) — exposes frontend on `:3000`, keeps backend on the internal network, mounts three volumes: `frontend-data` (audio), `backend-data` (SQLite), `backend-uploads` (reference docs).

## Observability

`observability.py` emits structured events + per-step timers; `log_store.py` persists them; `metrics.py` exposes counters. The UI consumes `/logs` and `/metrics` (proxied via `/api/logs`) for the admin/settings views.
