# Phase 2: AI Extraction and Promotion - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can trigger AI extraction on a completed transcript and get structured outcomes (decisions, action items, requirements, blockers) with confidence scores and evidence links to transcript utterances. Action items can be promoted to tasks and requirements to requirement records, both retaining backlinks to the source transcript. Admin review workflow and approval gating are v2 (REV-01/02).

</domain>

<decisions>
## Implementation Decisions

### Extraction Trigger & Pipeline
- Auto-trigger: extraction runs automatically after transcription completes — no manual button
- Runs on Python backend via llama.cpp with Phi-4-mini-instruct (3.8B, ~2.5GB GGUF Q4)
- Same sequential job queue as STT — one heavy model at a time (Moonshine OR Phi-4-mini, never both)
- Pipeline: Upload → [Queue] → STT → [Queue] → Extract
- One-shot extraction per transcript — no re-extract capability
- New backend endpoints: `POST /recordings/{id}/extract` (auto-called), `GET /recordings/{id}/outcomes`

### Outcome Display
- Results appear on an "Outcomes" tab on the recording detail page (alongside Info and Transcript tabs)
- While extracting: Outcomes tab shows processing spinner/skeleton state
- Summary banner at top: total outcomes, breakdown by type, count needing review
- Grouped cards by type: collapsible sections for Decisions, Action Items, Requirements, Blockers with count in header
- Each card shows: type icon, title (bold), 1-2 line detail excerpt, confidence score (numeric with color), evidence link, promote button (if applicable)

### Evidence Links
- Each outcome can reference 1-3 transcript utterances as evidence
- Evidence link shows primary utterance timestamp + speaker, with "+N more" expandable for additional references
- Clicking evidence: switches to Transcript tab, scrolls to utterance, highlights it yellow (fades after ~3 seconds)

### Confidence Flagging
- Confidence shown as numeric score (0.92) with color coding: green (≥0.80), amber (<0.80)
- Low-confidence items: amber left border on card, amber confidence badge, "Needs review" label
- Flag is informational only — users can still promote low-confidence items (admin approval gating is v2)
- 0.80 threshold is the dividing line

### Promotion Flow
- One-click instant promote — no modal, no editable fields before creation
- Promotion map: Action Items → Tasks, Requirements → Requirement Records
- Decisions and Blockers are informational only — no promotion available
- After promotion: toast notification ("Task created"), checkmark badge on card, "Promote" button replaced with "View Task" link
- Promoted items cannot be promoted again (button replaced permanently)

### Backlinks
- Promoted tasks/requirements include a simple text reference: recording name + timestamp (e.g., "From: Sprint Planning @ 2:34 — Speaker 1")
- No clickable deep-link back to transcript in v1 — just text metadata

### Claude's Discretion
- LLM prompt engineering for structured extraction (JSON schema, system prompt)
- Outcome card spacing, typography, and exact color palette
- Loading skeleton design for Outcomes tab
- Error state handling (extraction failure)
- How Phi-4-mini model is loaded/cached in the backend
- Exact toast notification timing and style
- How requirement records are stored (schema design)

</decisions>

<specifics>
## Specific Ideas

- Outcome cards should feel clean like the existing recording hub table — not cluttered
- Summary banner gives a quick "AI did its job" impression for FYP demo — professors see the extraction stats at a glance
- Evidence highlight on transcript (yellow fade) makes the AI-to-source connection tangible during demo
- Sequential queue ensures M3 Mac doesn't run out of memory — one heavy model at a time

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/components/ui/tabs.tsx` — Tab component already used for Recording Hub, reusable for Info/Transcript/Outcomes tabs
- `src/components/ui/badge.tsx` — Badge component for confidence scores and type labels
- `src/components/ui/skeleton.tsx` — Skeleton component for loading states
- `src/components/transcript/transcript-view.tsx` — Existing transcript display with chat bubbles (evidence highlight target)
- `src/types/recording.ts` — Utterance type with id, speaker, text, startTime, endTime (evidence link references)
- `backend/job_queue.py` — Existing async job queue for STT processing (extend for extraction)
- `backend/models.py` — Pydantic models for API responses (extend with outcome models)

### Established Patterns
- Frontend polls backend status endpoint for processing updates (reuse for extraction status)
- Next.js API routes proxy all backend calls — single origin pattern
- Backend uses Pydantic models for request/response validation
- SQLite (better-sqlite3) for frontend metadata, filesystem for audio storage
- Backend status flow: pending → processing → completed → failed

### Integration Points
- Recording detail page (`src/app/(dashboard)/recordings/[id]/page.tsx`) — add Outcomes tab
- Transcript proxy route (`src/app/api/recordings/[id]/transcript/route.ts`) — pattern for new outcomes proxy route
- Backend job queue (`backend/job_queue.py`) — extend to chain extraction after STT
- Frontend recording type needs extension for extraction status
- New SQLite tables needed: outcomes, tasks, requirements (frontend side)
- New backend endpoints: extract trigger + outcomes retrieval

</code_context>

<deferred>
## Deferred Ideas

- Admin approval workflow for low-confidence items (REV-01, REV-02) — v2
- Re-extraction capability (re-run AI on same transcript) — future enhancement
- Clickable deep-link backlinks from tasks back to transcript utterances — v2
- Bulk promote (select multiple outcomes and promote at once) — future enhancement

</deferred>

---

*Phase: 02-ai-extraction-and-promotion*
*Context gathered: 2026-03-12*

