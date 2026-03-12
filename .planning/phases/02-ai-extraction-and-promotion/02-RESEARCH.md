# Phase 2: AI Extraction and Promotion - Research

**Researched:** 2026-03-12
**Domain:** LLM-based structured extraction from transcripts + outcome promotion UI
**Confidence:** HIGH

## Summary

This phase adds AI extraction of structured outcomes (decisions, action items, requirements, blockers) from completed transcripts using Phi-4-mini-instruct (3.8B) via llama-cpp-python, then displays them in an Outcomes tab with confidence scoring and evidence links, and allows one-click promotion of action items to tasks and requirements to requirement records.

The backend work extends the existing sequential job queue to chain extraction after STT, adds a new extraction module using llama-cpp-python with GGUF quantized Phi-4-mini, and uses JSON schema-constrained generation for reliable structured output. The frontend work adds an Outcomes tab to the recording detail page, outcome cards grouped by type with confidence coloring, evidence links that cross-navigate to the transcript, and promotion flow with toast feedback.

**Primary recommendation:** Use `llama-cpp-python` with `response_format={"type": "json_object", "schema": ...}` for grammar-constrained JSON extraction, Q4_K_M quantization (~2.5GB), and chain extraction automatically in the job queue after STT completes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Auto-trigger: extraction runs automatically after transcription completes -- no manual button
- Runs on Python backend via llama.cpp with Phi-4-mini-instruct (3.8B, ~2.5GB GGUF Q4)
- Same sequential job queue as STT -- one heavy model at a time (Moonshine OR Phi-4-mini, never both)
- Pipeline: Upload -> [Queue] -> STT -> [Queue] -> Extract
- One-shot extraction per transcript -- no re-extract capability
- New backend endpoints: `POST /recordings/{id}/extract` (auto-called), `GET /recordings/{id}/outcomes`
- Results appear on an "Outcomes" tab on the recording detail page (alongside Info and Transcript tabs)
- While extracting: Outcomes tab shows processing spinner/skeleton state
- Summary banner at top: total outcomes, breakdown by type, count needing review
- Grouped cards by type: collapsible sections for Decisions, Action Items, Requirements, Blockers with count in header
- Each card shows: type icon, title (bold), 1-2 line detail excerpt, confidence score (numeric with color), evidence link, promote button (if applicable)
- Each outcome can reference 1-3 transcript utterances as evidence
- Evidence link shows primary utterance timestamp + speaker, with "+N more" expandable for additional references
- Clicking evidence: switches to Transcript tab, scrolls to utterance, highlights it yellow (fades after ~3 seconds)
- Confidence shown as numeric score (0.92) with color coding: green (>=0.80), amber (<0.80)
- Low-confidence items: amber left border on card, amber confidence badge, "Needs review" label
- Flag is informational only -- users can still promote low-confidence items
- 0.80 threshold is the dividing line
- One-click instant promote -- no modal, no editable fields before creation
- Promotion map: Action Items -> Tasks, Requirements -> Requirement Records
- Decisions and Blockers are informational only -- no promotion available
- After promotion: toast notification ("Task created"), checkmark badge on card, "Promote" button replaced with "View Task" link
- Promoted items cannot be promoted again (button replaced permanently)
- Backlinks are simple text reference: recording name + timestamp (e.g., "From: Sprint Planning @ 2:34 -- Speaker 1")
- No clickable deep-link back to transcript in v1 -- just text metadata

### Claude's Discretion
- LLM prompt engineering for structured extraction (JSON schema, system prompt)
- Outcome card spacing, typography, and exact color palette
- Loading skeleton design for Outcomes tab
- Error state handling (extraction failure)
- How Phi-4-mini model is loaded/cached in the backend
- Exact toast notification timing and style
- How requirement records are stored (schema design)

### Deferred Ideas (OUT OF SCOPE)
- Admin approval workflow for low-confidence items (REV-01, REV-02) -- v2
- Re-extraction capability (re-run AI on same transcript) -- future enhancement
- Clickable deep-link backlinks from tasks back to transcript utterances -- v2
- Bulk promote (select multiple outcomes and promote at once) -- future enhancement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXT-01 | AI extracts structured outcomes from transcript (decisions, action items, requirements, blockers) | llama-cpp-python + Phi-4-mini with JSON schema constraint; extraction module with structured prompt |
| EXT-02 | Each outcome includes title, details, confidence score, and evidence link to transcript utterance(s) | JSON output schema includes title, detail, confidence, evidence_refs fields; utterance IDs map to existing transcript segments |
| EXT-03 | Outcomes display grouped by type with confidence indicators | Frontend Outcomes tab with collapsible sections per type; Badge component for confidence |
| EXT-04 | Items below 0.80 confidence are visually flagged for review | Amber color coding on cards below threshold; CSS conditional classes |
| EXT-05 | User can promote action items to tasks with backlinks to source evidence | POST /api/recordings/{id}/outcomes/{outcomeId}/promote endpoint; tasks SQLite table; text backlink metadata |
| EXT-06 | User can promote requirements to requirement records with backlinks | Same promotion endpoint with type-aware routing; requirements SQLite table |
| EXT-07 | Promoted tasks/requirements retain evidence links to original transcript and audio timestamp | Backlink stored as text field: "From: {recording title} @ {timestamp} -- {speaker}" |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| llama-cpp-python | >=0.3.0 | Python bindings for llama.cpp, runs GGUF models | Only mature Python binding for llama.cpp; supports Metal on Apple Silicon; JSON schema-constrained generation via `response_format` |
| Phi-4-mini-instruct Q4_K_M GGUF | bartowski quant | 3.8B param LLM for extraction | User decision; 2.49GB fits M3 memory budget alongside app; MIT license |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| huggingface-hub[cli] | latest | Download GGUF model file | One-time model download during setup |
| sonner (already installed) | ^2.0.7 | Toast notifications for promotion feedback | Already in package.json; use for "Task created" toasts |
| zod (already installed) | ^4.3.6 | Frontend validation of outcome/task data | Already in package.json; validate API responses |
| lucide-react (already installed) | ^0.577.0 | Icons for outcome type badges | Already in package.json; use FileText, CheckSquare, AlertTriangle, Target icons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| llama-cpp-python | ctransformers | llama-cpp-python is more actively maintained, better Metal support, JSON schema grammar built-in |
| JSON schema constraint | Free-form generation + parse | Grammar constraint guarantees valid JSON every time; free-form risks malformed output |
| Q4_K_M quant | Q6_K (3.16GB) | Q4_K_M saves ~700MB RAM with minimal quality loss; critical for M3 memory budget |

**Installation (backend):**
```bash
# Install llama-cpp-python with Metal support for Apple Silicon
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python>=0.3.0

# Download model (one-time, ~2.5GB)
huggingface-cli download bartowski/microsoft_Phi-4-mini-instruct-GGUF \
  --include "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf" \
  --local-dir ./models/
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
  extraction.py          # LLM extraction logic (load model, run prompt, parse output)
  job_queue.py           # Extended: chain extraction after STT
  models.py              # Extended: Outcome, Task, RequirementRecord Pydantic models
  storage.py             # Extended: outcome/task/requirement persistence
  main.py                # Extended: new endpoints
  models/                # GGUF model files (gitignored)
    microsoft_Phi-4-mini-instruct-Q4_K_M.gguf

src/
  types/recording.ts     # Extended: Outcome, Task, RequirementRecord types
  types/outcome.ts       # New: outcome-specific types
  hooks/use-outcomes.ts  # New: outcome fetching + promotion hooks
  components/outcome/    # New: outcome display components
    outcomes-tab.tsx         # Tab container with summary banner + grouped sections
    outcome-card.tsx         # Individual outcome card
    outcome-section.tsx      # Collapsible section per type
    summary-banner.tsx       # Stats banner
  app/api/recordings/[id]/
    outcomes/route.ts        # Proxy to backend GET /recordings/{id}/outcomes
    extract/route.ts         # Proxy to backend POST /recordings/{id}/extract
  app/api/outcomes/[id]/
    promote/route.ts         # Promote outcome to task/requirement
  lib/db/
    schema.sql               # Extended: outcomes, tasks, requirements tables
    outcomes.ts              # CRUD for outcomes (frontend SQLite)
    tasks.ts                 # CRUD for tasks (frontend SQLite)
```

### Pattern 1: Chained Job Queue (Backend)
**What:** After STT completes, automatically enqueue extraction as a second job
**When to use:** Always -- this is the locked pipeline decision
**Example:**
```python
# In job_queue.py - modified process_worker
async def process_worker(app_state: object) -> None:
    while True:
        job_id, job_type = await job_queue.get()  # tuple: (id, "stt"|"extract")
        try:
            job = get_job(job_id)
            if job is None:
                continue

            if job_type == "stt":
                update_job(job_id, status="processing")
                result = await asyncio.to_thread(run_transcription, job_id, app_state)
                update_job(job_id, status="completed", result=result)
                # Auto-chain extraction
                update_job(job_id, extraction_status="pending")
                await job_queue.put((job_id, "extract"))

            elif job_type == "extract":
                update_job(job_id, extraction_status="processing")
                outcomes = await asyncio.to_thread(run_extraction, job_id, app_state)
                update_job(job_id, extraction_status="completed", outcomes=outcomes)

        except Exception as exc:
            if job_type == "stt":
                update_job(job_id, status="failed", error=str(exc))
            else:
                update_job(job_id, extraction_status="failed", extraction_error=str(exc))
        finally:
            job_queue.task_done()
```

### Pattern 2: JSON Schema-Constrained Extraction (Backend)
**What:** Use llama-cpp-python's `response_format` with JSON schema to guarantee valid structured output
**When to use:** For all LLM extraction calls
**Example:**
```python
from llama_cpp import Llama

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "outcomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["decision", "action_item", "requirement", "blocker"]},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "segment_index": {"type": "integer"},
                                "speaker": {"type": "string"},
                                "timestamp": {"type": "number"},
                                "text_snippet": {"type": "string"}
                            },
                            "required": ["segment_index", "speaker", "timestamp"]
                        }
                    }
                },
                "required": ["type", "title", "detail", "confidence", "evidence_refs"]
            }
        }
    },
    "required": ["outcomes"]
}

def run_extraction(job_id: str, app_state: object) -> list[dict]:
    job = get_job(job_id)
    transcript_text = format_transcript_for_prompt(job["result"]["segments"])

    response = app_state.llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript_text},
        ],
        response_format={"type": "json_object", "schema": EXTRACTION_SCHEMA},
        temperature=0.1,  # Low temperature for deterministic extraction
        max_tokens=4096,
    )

    content = response["choices"][0]["message"]["content"]
    return json.loads(content)["outcomes"]
```

### Pattern 3: Model Lazy Loading (Backend)
**What:** Load Phi-4-mini at startup (like Moonshine/SpeechBrain) but defer until first extraction request to avoid blocking startup with two heavy models
**When to use:** In lifespan context manager
**Example:**
```python
# Option A: Eager load at startup (simpler, longer startup)
app.state.llm = Llama(
    model_path="models/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf",
    n_ctx=4096,       # Context window (we only need ~4K for extraction)
    n_gpu_layers=-1,  # Offload all layers to Metal GPU
    chat_format="chatml",  # Phi-4-mini uses chatml-compatible format
    verbose=False,
)

# Option B: Lazy load on first extraction (recommended -- saves startup time)
# Load in run_extraction if app_state.llm is None
```

### Pattern 4: Frontend Status Polling Extension
**What:** Extend existing status polling to include extraction_status alongside transcription status
**When to use:** Recording detail page when status transitions from "ready" (STT done) to extraction states
**Example:**
```typescript
// Extended status response includes extraction_status
type ExtractionStatus = 'none' | 'pending' | 'processing' | 'completed' | 'failed';

// Poll while extracting, show Outcomes tab skeleton
// When extraction_status === 'completed', fetch outcomes
```

### Pattern 5: Evidence Cross-Navigation (Frontend)
**What:** Clicking evidence link in Outcomes tab switches to Transcript tab and highlights the utterance
**When to use:** Evidence links on outcome cards
**Example:**
```typescript
// Use a shared state (Zustand or React context) for cross-tab communication
// 1. Click evidence link -> set highlightUtteranceId in store
// 2. Switch active tab to "transcript"
// 3. TranscriptView reads highlightUtteranceId, scrolls to element, applies yellow highlight
// 4. After 3 seconds, clear highlight (CSS transition + timeout)
```

### Anti-Patterns to Avoid
- **Loading both Moonshine and Phi-4 simultaneously:** The sequential queue exists specifically to prevent this. Never parallelize these models on M3.
- **Free-form LLM output without schema constraint:** Always use `response_format` with a JSON schema. Free-form generation will produce malformed JSON in ~10-20% of cases with a 3.8B model.
- **Embedding full transcript in prompt for long meetings:** Phi-4-mini supports 128K context but performance degrades. Truncate or summarize transcripts over ~8K tokens for the prompt.
- **Storing outcomes only in backend in-memory store:** Outcomes must persist in frontend SQLite so they survive backend restarts. Backend in-memory store is volatile.
- **Building a complex promotion modal:** User decision is one-click instant promote. No modal, no form, no editable fields.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-constrained LLM output | Regex parsing of free-form text | llama-cpp-python `response_format` with JSON schema | Grammar-constrained decoding guarantees valid JSON structure |
| Toast notifications | Custom toast system | sonner (already installed) | Battle-tested, accessible, already in the project |
| Collapsible sections | Custom accordion | shadcn/ui Collapsible or Accordion | Already using shadcn pattern in the project |
| Tab component | Custom tabs | shadcn/ui Tabs (already used) | `src/components/ui/tabs.tsx` exists |
| GGUF model loading | Custom C++ bindings | llama-cpp-python | Maintained bindings with Metal support |
| Scroll-to-element | Manual offset calculation | `Element.scrollIntoView({ behavior: 'smooth', block: 'center' })` | Native browser API, works reliably |

**Key insight:** The LLM extraction itself is the hard part. Everything around it (display, promotion, evidence links) uses existing patterns and components from Phase 1.

## Common Pitfalls

### Pitfall 1: Model Loading Crashes Backend on Low Memory
**What goes wrong:** Loading Phi-4-mini (~2.5GB) while Moonshine + SpeechBrain are still in memory causes OOM on M3
**Why it happens:** All three models loaded simultaneously exceed available unified memory
**How to avoid:** The sequential queue prevents simultaneous inference, but all models remain loaded in memory. For M3 with 8GB unified memory, this should work (Moonshine ~300MB + SpeechBrain ~300MB + Phi-4 ~2.5GB = ~3.1GB). If issues arise, consider unloading Moonshine/SpeechBrain before extraction.
**Warning signs:** Process killed by OS, backend crashes with SIGKILL

### Pitfall 2: Phi-4-mini Hallucinating Segment Indices
**What goes wrong:** The LLM references segment indices that don't exist in the transcript
**Why it happens:** Small models hallucinate numerical references, especially with JSON schema constraints
**How to avoid:** Validate all segment_index values against actual transcript length after extraction. Clamp or discard invalid references. Include segment indices explicitly in the prompt text.
**Warning signs:** Evidence links point to non-existent utterances, IndexError on frontend

### Pitfall 3: Extraction Takes Too Long for Demo
**What goes wrong:** Phi-4-mini with Q4_K_M on CPU/Metal takes >60 seconds for a 5-minute meeting transcript
**Why it happens:** 3.8B model inference is CPU-bound; long transcripts mean long prompts and long generations
**How to avoid:** Use n_gpu_layers=-1 to offload everything to Metal GPU. Keep prompt under ~4K tokens (summarize long transcripts). Set max_tokens=4096 for output. Use temperature=0.1 for faster convergence.
**Warning signs:** Extraction jobs stuck in "processing" for minutes

### Pitfall 4: Backend In-Memory Store Loses Outcomes on Restart
**What goes wrong:** Outcomes stored only in `storage.py` dict are lost when backend restarts
**Why it happens:** The existing backend uses in-memory storage (dict), not a database
**How to avoid:** Two options: (A) Store outcomes in the in-memory store like transcripts -- acceptable for FYP demo since it's a single session. (B) Write outcomes to a JSON file alongside the transcript. Option A is simplest and consistent with existing pattern.
**Warning signs:** Outcomes disappear after backend restart

### Pitfall 5: Chat Format Mismatch
**What goes wrong:** llama-cpp-python uses wrong chat template, producing garbled output
**Why it happens:** Phi-4-mini uses `<|system|>...<|end|><|user|>...<|end|><|assistant|>` format, which maps to "chatml" in llama-cpp-python but may need explicit configuration
**How to avoid:** Set `chat_format="chatml"` when initializing Llama, or let it auto-detect from GGUF metadata. Test with a simple extraction before building the full pipeline.
**Warning signs:** Model produces nonsensical output, repeated tokens, or ignores system prompt

### Pitfall 6: Frontend Tab State Not Synced with Extraction Status
**What goes wrong:** User sees empty Outcomes tab because extraction hasn't started/completed yet
**Why it happens:** The recording status says "ready" (STT done) but extraction is still running
**How to avoid:** Add extraction_status to the status endpoint response. Frontend shows different states: "Extracting..." spinner, completed outcomes, or error state. Poll extraction_status separately from recording status.
**Warning signs:** Empty Outcomes tab when outcomes should be there

## Code Examples

### Backend: Extraction Module Structure
```python
# backend/extraction.py
"""LLM-based structured extraction from transcripts."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI meeting analyst. Extract structured outcomes from the meeting transcript below.

For each outcome, identify:
- type: one of "decision", "action_item", "requirement", "blocker"
- title: concise 5-10 word summary
- detail: 1-2 sentence description
- confidence: 0.0-1.0 how certain you are this is a real outcome (not casual discussion)
- evidence_refs: 1-3 transcript segments that support this outcome

Rules:
- Only extract clear, actionable outcomes -- not casual discussion or greetings
- Decisions: explicit group agreements or choices made
- Action items: tasks someone committed to doing, with implied or explicit ownership
- Requirements: stated needs, specifications, or constraints for the project
- Blockers: identified obstacles, risks, or dependencies that block progress
- Set confidence below 0.80 for ambiguous items or uncertain interpretations
- Reference segment indices exactly as provided in the transcript

Output valid JSON matching the required schema."""


def format_transcript_for_prompt(segments: list[dict[str, Any]]) -> str:
    """Format transcript segments into a numbered prompt-friendly format."""
    lines = []
    for i, seg in enumerate(segments):
        timestamp = f"{int(seg['start'] // 60)}:{int(seg['start'] % 60):02d}"
        lines.append(f"[{i}] {timestamp} {seg['speaker']}: {seg['text']}")
    return "\n".join(lines)


def run_extraction(job_id: str, app_state: object) -> list[dict[str, Any]]:
    """Run LLM extraction on a completed transcript."""
    from storage import get_job

    job = get_job(job_id)
    if job is None or job.get("result") is None:
        raise ValueError(f"Job {job_id} has no transcript result")

    segments = job["result"]["segments"]
    transcript_text = format_transcript_for_prompt(segments)

    response = app_state.llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript_text}"},
        ],
        response_format={
            "type": "json_object",
            "schema": EXTRACTION_SCHEMA,  # defined as constant
        },
        temperature=0.1,
        max_tokens=4096,
    )

    content = response["choices"][0]["message"]["content"]
    outcomes = json.loads(content)["outcomes"]

    # Validate segment indices
    max_idx = len(segments) - 1
    for outcome in outcomes:
        outcome["evidence_refs"] = [
            ref for ref in outcome["evidence_refs"]
            if 0 <= ref["segment_index"] <= max_idx
        ]

    return outcomes
```

### Backend: Pydantic Models for Outcomes
```python
# Additions to backend/models.py
from pydantic import BaseModel, Field

class EvidenceRef(BaseModel):
    segment_index: int
    speaker: str
    timestamp: float
    text_snippet: str = ""

class Outcome(BaseModel):
    id: str
    type: Literal["decision", "action_item", "requirement", "blocker"]
    title: str
    detail: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef]
    promoted: bool = False
    promoted_id: str | None = None  # ID of created task/requirement

class OutcomesResponse(BaseModel):
    job_id: str
    extraction_status: Literal["pending", "processing", "completed", "failed"]
    outcomes: list[Outcome] = []
```

### Frontend: Outcome Types
```typescript
// src/types/outcome.ts
export type OutcomeType = 'decision' | 'action_item' | 'requirement' | 'blocker';
export type ExtractionStatus = 'none' | 'pending' | 'processing' | 'completed' | 'failed';

export interface EvidenceRef {
  segmentIndex: number;
  speaker: string;
  timestamp: number;
  textSnippet?: string;
}

export interface Outcome {
  id: string;
  type: OutcomeType;
  title: string;
  detail: string;
  confidence: number;
  evidenceRefs: EvidenceRef[];
  promoted: boolean;
  promotedId: string | null;
}

export interface OutcomesResponse {
  jobId: string;
  extractionStatus: ExtractionStatus;
  outcomes: Outcome[];
}

export interface Task {
  id: string;
  title: string;
  detail: string;
  sourceOutcomeId: string;
  sourceRecordingId: string;
  backlink: string;  // "From: Sprint Planning @ 2:34 -- Speaker 1"
  createdAt: string;
}

export interface RequirementRecord {
  id: string;
  title: string;
  detail: string;
  sourceOutcomeId: string;
  sourceRecordingId: string;
  backlink: string;
  createdAt: string;
}
```

### Frontend: Evidence Highlight Pattern
```typescript
// Zustand store for cross-tab communication
import { create } from 'zustand';

interface EvidenceHighlightStore {
  highlightUtteranceId: string | null;
  activeTab: string;
  setHighlight: (utteranceId: string) => void;
  clearHighlight: () => void;
  setActiveTab: (tab: string) => void;
}

export const useEvidenceHighlight = create<EvidenceHighlightStore>((set) => ({
  highlightUtteranceId: null,
  activeTab: 'outcomes',
  setHighlight: (utteranceId) => {
    set({ highlightUtteranceId: utteranceId, activeTab: 'transcript' });
    // Auto-clear after 3 seconds
    setTimeout(() => set({ highlightUtteranceId: null }), 3000);
  },
  clearHighlight: () => set({ highlightUtteranceId: null }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
```

### SQLite Schema Extensions (Frontend)
```sql
-- New tables for frontend SQLite
CREATE TABLE IF NOT EXISTS outcomes (
  id TEXT PRIMARY KEY,
  recording_id TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('decision','action_item','requirement','blocker')),
  title TEXT NOT NULL,
  detail TEXT NOT NULL,
  confidence REAL NOT NULL,
  evidence_refs TEXT NOT NULL DEFAULT '[]',  -- JSON array
  promoted INTEGER NOT NULL DEFAULT 0,
  promoted_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (recording_id) REFERENCES recordings(id)
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  detail TEXT NOT NULL,
  source_outcome_id TEXT,
  source_recording_id TEXT,
  backlink TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (source_outcome_id) REFERENCES outcomes(id),
  FOREIGN KEY (source_recording_id) REFERENCES recordings(id)
);

CREATE TABLE IF NOT EXISTS requirement_records (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  detail TEXT NOT NULL,
  source_outcome_id TEXT,
  source_recording_id TEXT,
  backlink TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (source_outcome_id) REFERENCES outcomes(id),
  FOREIGN KEY (source_recording_id) REFERENCES recordings(id)
);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-form LLM text parsing with regex | JSON schema-constrained generation via GBNF grammars | llama.cpp 2024+ | Guarantees valid JSON output, no parsing failures |
| Python ctransformers bindings | llama-cpp-python (abetlen) | 2024 | Most active maintenance, Metal support, JSON schema support |
| Large cloud LLMs for extraction | Small local models (3-4B params) with structured output | 2024-2025 | Privacy-preserving, no API costs, offline-capable |

**Deprecated/outdated:**
- ctransformers: No longer actively maintained, use llama-cpp-python instead
- llama-cpp-python versions <0.2.0: Missing JSON schema response_format support

## Open Questions

1. **Phi-4-mini extraction quality for meeting transcripts**
   - What we know: 3.8B models can do structured extraction reasonably well with schema constraints
   - What's unclear: Specific quality for meeting-style transcripts with diarization labels
   - Recommendation: Build extraction module first, test with a real transcript, tune system prompt iteratively. The STATE.md notes this as a known risk: "LLM extraction reliability with quantized model needs early validation"

2. **Memory budget on M3 with all models loaded**
   - What we know: Moonshine ~300MB + SpeechBrain ECAPA ~300MB + Phi-4 Q4_K_M ~2.5GB = ~3.1GB models
   - What's unclear: Peak memory during inference, macOS overhead
   - Recommendation: Monitor Activity Monitor during first integration test. If tight, consider lazy-loading Phi-4 only when extraction starts (and potentially unloading STT models).

3. **Extraction latency acceptable for demo**
   - What we know: Metal GPU acceleration available, Q4_K_M is fast quant
   - What's unclear: Wall-clock time for a 5-minute meeting transcript on M3
   - Recommendation: Target under 30 seconds. If slower, show clear progress indicator. Consider truncating very long transcripts.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | Vitest 4.x + happy-dom |
| Framework (backend) | pytest 8.x + pytest-asyncio |
| Config file (frontend) | vitest.config.ts |
| Config file (backend) | backend/pyproject.toml [tool.pytest.ini_options] |
| Quick run command (frontend) | `npx vitest run --reporter=verbose` |
| Quick run command (backend) | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `npx vitest run && cd backend && python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXT-01 | Extraction produces structured outcomes from transcript text | unit (backend) | `cd backend && python -m pytest tests/test_extraction.py::test_extraction_produces_outcomes -x` | Wave 0 |
| EXT-02 | Each outcome has title, detail, confidence, evidence_refs | unit (backend) | `cd backend && python -m pytest tests/test_extraction.py::test_outcome_schema_validation -x` | Wave 0 |
| EXT-03 | Outcomes display grouped by type | unit (frontend) | `npx vitest run src/components/outcome/__tests__/outcomes-tab.test.tsx` | Wave 0 |
| EXT-04 | Low confidence items visually flagged | unit (frontend) | `npx vitest run src/components/outcome/__tests__/outcome-card.test.tsx` | Wave 0 |
| EXT-05 | Promote action item to task | integration (backend+frontend) | `cd backend && python -m pytest tests/test_api.py::test_promote_action_item -x` | Wave 0 |
| EXT-06 | Promote requirement to record | integration (backend+frontend) | `cd backend && python -m pytest tests/test_api.py::test_promote_requirement -x` | Wave 0 |
| EXT-07 | Backlinks retained on promoted items | unit (backend) | `cd backend && python -m pytest tests/test_extraction.py::test_backlink_format -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run --reporter=verbose` (frontend) + `cd backend && python -m pytest tests/ -x -q` (backend)
- **Per wave merge:** Full suite across both frontend and backend
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_extraction.py` -- covers EXT-01, EXT-02, EXT-07 (mock LLM, test schema validation and backlink format)
- [ ] `src/components/outcome/__tests__/outcomes-tab.test.tsx` -- covers EXT-03
- [ ] `src/components/outcome/__tests__/outcome-card.test.tsx` -- covers EXT-04
- [ ] Backend promotion endpoint tests in `backend/tests/test_api.py` -- covers EXT-05, EXT-06

## Sources

### Primary (HIGH confidence)
- [bartowski/microsoft_Phi-4-mini-instruct-GGUF](https://huggingface.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF) - Quantization options, file sizes, download instructions
- [microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) - Chat template format, model capabilities, known limitations
- [llama-cpp-python docs](https://llama-cpp-python.readthedocs.io/) - JSON schema response_format API, Metal installation
- [abetlen/llama-cpp-python GitHub](https://github.com/abetlen/llama-cpp-python) - Python bindings API reference
- Existing codebase: `backend/job_queue.py`, `backend/storage.py`, `backend/transcription.py`, `backend/main.py` - Current architecture patterns

### Secondary (MEDIUM confidence)
- [Instructor llama-cpp-python integration](https://python.useinstructor.com/integrations/llama-cpp-python/) - Structured output patterns verified with docs
- [Simon Willison's TIL on llama-cpp-python grammars](https://til.simonwillison.net/llms/llama-cpp-python-grammars) - Grammar-based JSON generation

### Tertiary (LOW confidence)
- Phi-4-mini extraction quality for meeting transcripts: No benchmark data found specific to meeting extraction with Q4 quant. Flagged as risk in STATE.md.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - llama-cpp-python is the established Python binding; Phi-4-mini GGUF availability confirmed on HuggingFace
- Architecture: HIGH - Extends existing patterns (job queue, in-memory store, proxy routes, polling) from Phase 1
- Pitfalls: HIGH - Memory constraints and model quality are well-documented concerns for small quantized models
- Extraction quality: LOW - No specific benchmarks for meeting transcript extraction with Phi-4-mini Q4

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain; llama-cpp-python releases frequently but API is stable)
