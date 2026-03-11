# Architecture Patterns

**Domain:** AI-powered meeting-to-project-plan system
**Researched:** 2026-03-11

## Recommended Architecture

### High-Level Overview

```
+-----------------------------------------------------------+
|                    Next.js Frontend                        |
|  [Recording UI] [Transcript Editor] [Review] [Tasks/PM]   |
+----------------------------+------------------------------+
                             | REST / SSE
                             v
+-----------------------------------------------------------+
|                  Python FastAPI Backend                     |
|  [Recording Mgmt] [STT Pipeline] [LLM Pipeline] [CRUD]   |
+----------------------------+------------------------------+
          |              |              |
          v              v              v
     [SQLite DB]   [Filesystem]   [llama.cpp]
     (metadata,    (~/.allure/     (local LLM
      tasks,        recordings/)    inference)
      outcomes)
```

The system follows a **pipeline architecture** where data flows through distinct stages: Capture, Transcribe, Extract, Review, Promote. Each stage has a clear input/output contract, and the frontend orchestrates user interaction at each gate.

### Component Boundaries

| Component | Responsibility | Communicates With | Boundary Type |
|-----------|---------------|-------------------|---------------|
| **Recording Capture (Frontend)** | Browser MediaRecorder API, audio capture, upload | Backend Recording API | HTTP multipart upload |
| **Recording Hub (Frontend)** | Status tracking, assignment, list/filter recordings | Backend Recording API | REST GET/PATCH |
| **STT Pipeline (Backend)** | Whisper transcription + speaker diarization | Filesystem (audio in), SQLite (transcript out) | Internal, async job |
| **Transcript Editor (Frontend)** | Display/edit transcript, synced audio playback | Backend Transcript API | REST GET/PUT |
| **LLM Extraction Pipeline (Backend)** | Extract decisions, action items, requirements, blockers from transcript | llama.cpp (inference), SQLite (outcomes out) | Internal, async job |
| **Outcome Review (Frontend)** | Confidence-gated review UI, approve/reject/edit outcomes | Backend Outcomes API | REST GET/PATCH |
| **Task/PM Module (Frontend)** | Task CRUD, Kanban, milestones, dependencies | Backend Tasks API | REST full CRUD |
| **Document Generation (Backend)** | PRD generation, Mermaid diagrams from project data | llama.cpp (generation), SQLite (project data in) | Internal, triggered by frontend |
| **Notification System (Frontend)** | In-app notifications for status changes | Backend via SSE or polling | SSE preferred |

### Critical Boundary: Frontend vs Backend Responsibility

The frontend is a **thin orchestration layer**. All AI inference, file processing, and business logic lives in the backend. The frontend handles:
- User interaction and state management
- Audio capture via browser APIs
- Display and editing of backend-produced data
- Status polling / real-time updates for async operations

The backend owns:
- All Whisper/LLM inference
- File storage management
- Data persistence and validation
- Confidence scoring and threshold logic

## Data Flow

### Primary Pipeline: Recording to Tasks

```
1. CAPTURE
   User clicks Record -> Browser MediaRecorder captures audio
   -> Upload to POST /api/recordings (multipart/form-data)
   -> Backend saves to ~/.allure/recordings/{id}.webm
   -> SQLite: recording row (status: "unassigned" or "uploaded")

2. ASSIGN (optional, can be deferred)
   User assigns recording to a project
   -> PATCH /api/recordings/{id} { project_id }
   -> SQLite: update recording.project_id

3. TRANSCRIBE (async)
   User triggers transcription (or auto-triggered on upload)
   -> POST /api/recordings/{id}/transcribe
   -> Backend queues STT job:
      a. Load audio from filesystem
      b. Whisper inference -> raw transcript
      c. Speaker diarization -> labeled utterances
      d. Confidence scores per segment
   -> SQLite: transcript rows linked to recording
   -> Recording status: "processing" -> "transcribed"
   -> Frontend polls GET /api/recordings/{id}/status
     OR receives SSE event

4. REVIEW TRANSCRIPT
   User views/edits transcript in synced editor
   -> GET /api/recordings/{id}/transcript
   -> PUT /api/transcripts/{id}/utterances/{utterance_id}
   -> Audio playback synced via timestamp offsets

5. EXTRACT (async)
   User triggers outcome extraction
   -> POST /api/recordings/{id}/extract
   -> Backend queues LLM job:
      a. Build prompt from transcript + context
      b. llama.cpp inference -> structured JSON
      c. Parse: decisions, action_items, requirements, blockers
      d. Assign confidence scores to each outcome
      e. Link outcomes to source utterances (evidence)
   -> SQLite: outcome rows with confidence, evidence_links
   -> Recording status: "extracted" / "needs_review"

6. REVIEW OUTCOMES
   Frontend displays outcomes grouped by type
   -> GET /api/recordings/{id}/outcomes
   -> Items >= 0.80 confidence: auto-approved (or shown as approved)
   -> Items < 0.80: require Admin review
   -> PATCH /api/outcomes/{id} { status: "approved" | "rejected", edits }

7. PROMOTE
   Approved outcomes become tasks/milestones/requirements
   -> POST /api/outcomes/{id}/promote
   -> Backend creates task/milestone/requirement rows in SQLite
   -> Backlinks maintained: task.source_outcome_id -> outcome.id
   -> Outcome status: "promoted"

8. PLAN (optional)
   AI generates milestone structure from promoted outcomes
   -> POST /api/projects/{id}/generate-plan
   -> LLM builds task dependencies, milestones, timeline
   -> User reviews and approves generated plan
```

### Secondary Flows

**Document Generation:**
```
Project data (tasks, requirements, outcomes)
-> POST /api/projects/{id}/generate-prd
-> LLM builds PRD from template + project data
-> Returns markdown document
-> Frontend renders with live preview
```

**Slide Alignment (if time permits):**
```
Upload PPTX/PDF -> POST /api/projects/{id}/documents
-> Backend extracts text/slides
-> Align transcript segments to slide content via embedding similarity
-> GET /api/recordings/{id}/transcript?with_slides=true
```

## Patterns to Follow

### Pattern 1: Async Job with Status Polling

All long-running operations (STT, LLM extraction, document generation) follow the same pattern. This is the most important architectural pattern in the system.

**What:** Client initiates an async job, backend processes in background, client polls or receives SSE for completion.

**When:** Any operation involving Whisper or llama.cpp inference (seconds to minutes).

**Implementation:**

```typescript
// Frontend: Trigger and poll pattern
async function triggerTranscription(recordingId: string) {
  // 1. Trigger the job
  await fetch(`/api/recordings/${recordingId}/transcribe`, { method: 'POST' });

  // 2. Poll for completion (or use SSE)
  const poll = setInterval(async () => {
    const res = await fetch(`/api/recordings/${recordingId}/status`);
    const { status } = await res.json();
    if (status === 'transcribed' || status === 'error') {
      clearInterval(poll);
      // Update UI
    }
  }, 2000); // Poll every 2 seconds
}
```

```python
# Backend: Background task pattern (FastAPI)
from fastapi import BackgroundTasks

@app.post("/api/recordings/{recording_id}/transcribe")
async def transcribe(recording_id: str, background_tasks: BackgroundTasks):
    update_status(recording_id, "processing")
    background_tasks.add_task(run_stt_pipeline, recording_id)
    return {"status": "processing"}
```

**Why:** Local inference on M3 Mac takes 10-60+ seconds. Synchronous requests would timeout. This pattern keeps the UI responsive.

### Pattern 2: Confidence-Gated Review

**What:** Every AI-produced artifact carries a confidence score. Items below threshold require human review before they become authoritative.

**When:** After LLM extraction produces outcomes, after QA scoring.

**Implementation:**

```typescript
// Frontend: Partition outcomes by confidence
interface Outcome {
  id: string;
  type: 'decision' | 'action_item' | 'requirement' | 'blocker';
  content: string;
  confidence: number;
  status: 'pending' | 'approved' | 'rejected';
  evidence_links: { utterance_id: string; text: string }[];
}

function partitionOutcomes(outcomes: Outcome[], threshold = 0.80) {
  return {
    approved: outcomes.filter(o => o.confidence >= threshold),
    needsReview: outcomes.filter(o => o.confidence < threshold),
  };
}
```

**Why:** LLM extraction is imperfect. Confidence gating prevents hallucinated outcomes from becoming real tasks without human verification.

### Pattern 3: Evidence Backlinks

**What:** Every promoted task/requirement maintains a link back to the source outcome, which links back to source transcript utterances, which link to audio timestamps.

**When:** Whenever data flows from one pipeline stage to the next.

**Data Model:**

```
Task -> source_outcome_id -> Outcome -> evidence_links -> Utterance -> audio_offset
```

**Why:** Auditability. Users can trace any task back to "who said this, when, in which meeting." This is a core differentiator over generic task managers.

### Pattern 4: Recording State Machine

**What:** Recordings follow a strict state machine that drives UI and available actions.

```
                    +-> assigned --+
                    |              |
unassigned ---------+              +-> processing -> transcribed -> extracted -> needs_review -> reviewed
                    |              |
                    +--------------+
                                   |
                                   +-> error (at any processing step)
```

**When:** Always. Every recording has exactly one status.

**Why:** The Recording Hub UI, available actions, and notification triggers all derive from this state. A clear state machine prevents impossible states and simplifies frontend logic.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Streaming LLM Output to Frontend

**What:** Streaming llama.cpp token-by-token output to the browser for extraction tasks.

**Why bad:** Extraction needs structured JSON output, not streaming text. Partial JSON is unparseable. Streaming adds complexity (WebSocket/SSE for partial results) with zero user value for extraction. The user cares about the final structured result, not watching tokens appear.

**Instead:** Use the async job pattern. Show a progress indicator. Return complete structured results.

**Exception:** Document generation (PRD) could benefit from streaming for perceived performance, but only implement this if time allows. For FYP, batch response is fine.

### Anti-Pattern 2: Frontend-Side AI Processing

**What:** Running Whisper.cpp or llama.cpp via WASM in the browser.

**Why bad:** Browser WASM inference is 5-10x slower than native Metal on M3. Memory constraints. Model loading time. The backend already has the pipeline.

**Instead:** All inference in the Python backend via native binaries. Frontend is a thin UI layer.

### Anti-Pattern 3: Monolithic API Endpoints

**What:** Single endpoint like `POST /api/recordings/{id}/process` that does transcription + extraction + promotion in one call.

**Why bad:** Each stage can fail independently. Users need to review between stages. A single long-running call (potentially 5+ minutes) is fragile.

**Instead:** Separate endpoints per pipeline stage. Each stage is independently triggerable and recoverable.

### Anti-Pattern 4: Over-Normalizing the SQLite Schema

**What:** Creating dozens of join tables for every relationship.

**Why bad:** SQLite is single-writer. Complex joins on a local DB add latency for no benefit at FYP scale. The data model is modest (hundreds of recordings, not millions).

**Instead:** Keep the schema pragmatic. Store evidence_links as JSON arrays in the outcomes table. Use foreign keys for real relationships (recording -> project, outcome -> recording, task -> outcome) but don't over-engineer.

## Component Build Order

Build order is driven by the pipeline: you cannot build downstream components without upstream ones producing data.

```
Phase 1: Foundation
  [Recording Capture] + [Recording Hub] + [Backend Recording API]
  Why first: Everything starts with a recording. No recording = nothing to process.
  Dependency: None (browser MediaRecorder + file upload is self-contained)

Phase 2: Transcription Loop
  [STT Pipeline Integration] + [Transcript Editor] + [Status Polling]
  Why second: Transcription is the next pipeline stage. Connects to existing backend Whisper.
  Dependency: Phase 1 (needs recordings to transcribe)

Phase 3: AI Extraction + Review
  [LLM Extraction Trigger] + [Outcome Review UI] + [Confidence Gating]
  Why third: This is the core AI value. Extraction needs transcripts.
  Dependency: Phase 2 (needs transcripts to extract from)

Phase 4: Task Management + Promotion
  [Task CRUD] + [Kanban/List Views] + [Promote Outcomes -> Tasks] + [Dependencies]
  Why fourth: Tasks are the output of the pipeline. Promotion connects extraction to PM.
  Dependency: Phase 3 (outcomes to promote) but Task CRUD can start in parallel

Phase 5: Document Generation + Polish
  [PRD Generation] + [Diagram Generation] + [Notifications] + [QA Agent]
  Why last: These are value-adds on top of the core pipeline.
  Dependency: Phase 4 (needs project data to generate docs from)
```

**Parallelization opportunity:** Task CRUD (Phase 4 frontend) can be built in parallel with Phase 2-3 since it is a standard CRUD UI. Wire up promotion later.

## API Contract Shape

The backend likely already has some of these endpoints. The frontend should expect this contract shape:

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/recordings` | GET | List recordings with filters | `Recording[]` |
| `/api/recordings` | POST | Upload new recording | `Recording` |
| `/api/recordings/{id}` | PATCH | Update (assign project, edit) | `Recording` |
| `/api/recordings/{id}/transcribe` | POST | Trigger STT pipeline | `{ status: "processing" }` |
| `/api/recordings/{id}/status` | GET | Poll processing status | `{ status, progress? }` |
| `/api/recordings/{id}/transcript` | GET | Get transcript with utterances | `Transcript` |
| `/api/recordings/{id}/extract` | POST | Trigger LLM extraction | `{ status: "processing" }` |
| `/api/recordings/{id}/outcomes` | GET | Get extracted outcomes | `Outcome[]` |
| `/api/outcomes/{id}` | PATCH | Approve/reject/edit outcome | `Outcome` |
| `/api/outcomes/{id}/promote` | POST | Promote to task/requirement | `Task` |
| `/api/projects/{id}/tasks` | GET/POST | Task CRUD | `Task[]` / `Task` |
| `/api/projects/{id}/milestones` | GET/POST | Milestone CRUD | `Milestone[]` |
| `/api/projects/{id}/generate-plan` | POST | AI plan generation | `{ status: "processing" }` |
| `/api/projects/{id}/generate-prd` | POST | PRD generation | `{ status: "processing" }` |

**Note:** Verify these against the actual existing backend API. The backend may already implement some of these differently. Adapt the frontend to match, not the other way around.

## Scalability Considerations

| Concern | FYP Scale (1-5 users) | If Scaling Later |
|---------|----------------------|------------------|
| Concurrent inference | Single queue, one job at a time | Job queue with priority (Redis + Celery) |
| SQLite writes | Single writer is fine | Migrate to PostgreSQL |
| Audio storage | Filesystem is fine | Object storage (S3/MinIO) |
| Real-time updates | Polling every 2s is fine | WebSocket or SSE |
| LLM context window | 8K context fits most meetings | Chunked extraction for long meetings |

For FYP: Do not optimize for scale. Single-user, single-job-at-a-time is perfectly acceptable and dramatically simpler.

## Key Data Model (SQLite)

```sql
-- Core entities
projects (id, name, created_at, updated_at)
recordings (id, project_id, file_path, status, duration, created_at)
transcripts (id, recording_id, created_at)
utterances (id, transcript_id, speaker, text, start_time, end_time, confidence)

-- AI extraction
outcomes (id, recording_id, type, content, confidence, status, evidence_links_json, created_at)

-- Project management
tasks (id, project_id, source_outcome_id, title, description, status, priority, due_date)
task_dependencies (task_id, depends_on_task_id)
milestones (id, project_id, title, due_date, status)
milestone_tasks (milestone_id, task_id)

-- Documents
documents (id, project_id, type, content_md, created_at)
```

**Note:** Verify against the existing backend schema. Adapt frontend expectations to match what exists.

## Sources

- Architecture patterns derived from domain knowledge of STT/LLM pipeline systems, FastAPI async patterns, and browser MediaRecorder API capabilities.
- Confidence: MEDIUM -- based on established patterns for async AI pipelines and local-first architectures, but not verified against external sources due to search limitations. The patterns (async jobs, state machines, confidence gating) are well-established in production systems like Otter.ai, Fireflies.ai, and similar meeting intelligence products.
- The existing backend repo (github.com/ZainAbbas97/allure-ai) should be consulted to verify API contracts and data models match what is already implemented.
