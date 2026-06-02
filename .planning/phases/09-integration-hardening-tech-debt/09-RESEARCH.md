# Phase 9: Integration Hardening & Tech Debt Cleanup - Research

**Researched:** 2026-03-20
**Domain:** Integration hardening, Pydantic model alignment, race condition resolution, documentation cleanup
**Confidence:** HIGH

## Summary

Phase 9 is a gap-closure phase driven by the v1.1 milestone audit. It addresses 3 code issues (INT-01 SpeakerStats model fragility, INT-02/FLOW-01 backendId race condition, function-level import) and 2 documentation gaps (REQUIREMENTS.md checkboxes, ROADMAP.md plan checkboxes). All issues are well-scoped with clear fixes identified in the audit report.

The SpeakerStats Pydantic model in `backend/models.py` is missing `custom_label` and `role` fields that the backend already produces (via `transcription.py:identify_speakers_with_llm`). The transcript endpoint returns raw dicts, masking the mismatch. The document upload route (`src/app/api/recordings/[id]/documents/route.ts`) has a race condition where `backendId` may be null when the post-recording dialog saves, causing documents to be saved to disk but never forwarded for text extraction. The `import re` on line 263 of `document_generation.py` should be moved to the top of the file.

**Primary recommendation:** Single plan with 2 code tasks (backend model fix + frontend race condition fix) and 1 documentation task. All changes are isolated and low-risk.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPKR-01 | User can edit speaker labels | INT-01 fix ensures SpeakerStats model carries `custom_label` through Pydantic validation |
| SPKR-02 | User can assign roles to speakers | INT-01 fix ensures SpeakerStats model carries `role` through Pydantic validation |
| RUX-02 | User can upload reference documents in post-recording popup | INT-02/FLOW-01 fix ensures documents uploaded from dialog are forwarded for extraction |
| DOC-02 | Attached document text is extracted and stored for generation context | INT-02/FLOW-01 fix ensures extraction happens even when backendId is not yet available |
| GEN-02 | PRD and Mermaid generation uses attached document text as context | Depends on DOC-02 extraction completing; race condition fix ensures document context is available |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Relevant To |
|---------|---------|---------|-------------|
| Pydantic | v2.x | Request/response models | INT-01: SpeakerStats field additions |
| FastAPI | latest | Backend API | Transcript endpoint, response_model |
| Next.js 15 | App Router | Frontend API routes | INT-02: documents/route.ts fix |
| better-sqlite3 | - | SQLite DB | Recording backendId lookups |

### No new libraries needed
This phase modifies existing code only. No new dependencies.

## Architecture Patterns

### Pattern 1: Pydantic Model with Optional Defaults (INT-01 Fix)

**What:** Add optional fields with defaults to `SpeakerStats` so the model accepts both old data (without custom_label/role) and new data (with them).

**Example:**
```python
class SpeakerStats(BaseModel):
    """Per-speaker statistics."""
    label: str
    talk_time_pct: float
    utterance_count: int
    talk_time: float
    word_count: int
    wpm: float
    turns: int
    avg_turn_duration: float
    pauses: int
    avg_pause_duration: float
    custom_label: str = ""    # Added: user-assigned name
    role: str = "Participant" # Added: user-assigned role
```

**Why defaults matter:** The `calculate_speaker_stats` function in `transcription.py` does NOT set these fields -- they are added later by `identify_speakers_with_llm`. Using `= ""` and `= "Participant"` ensures backward compatibility with any stats objects that haven't been through the LLM identification step.

### Pattern 2: Deferred Forwarding with Polling/Retry (INT-02 Fix)

**What:** When the documents route finds `backendId` is null, instead of silently skipping extraction, it should either:
- **Option A (Recommended): Poll for backendId** -- after saving files to disk, wait briefly and re-check `backendId` with a small retry loop. The audio upload to backend typically completes within seconds.
- **Option B: Queue for later** -- save a flag in the DB and have a mechanism retry forwarding when backendId becomes available.

**Recommended approach (Option A):** A simple retry with small delay in the documents route. The recording FAB fires the upload immediately (`uploadRecording.mutate`) which hits `POST /api/recordings` which does `fetch(BACKEND_URL/recordings)` synchronously before returning. The post-recording dialog opens simultaneously, but the user must fill in fields before hitting Save, giving the backend upload time to complete. The race window is narrow -- only if the user saves the dialog nearly instantly AND the backend is slow.

```typescript
// In documents/route.ts, after saving files:
let backendId = recording?.backendId

// If backendId not yet available, retry a few times
if (!backendId) {
  for (let attempt = 0; attempt < 5; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 1000))
    const freshRecording = getRecording(recordingId)
    if (freshRecording?.backendId) {
      backendId = freshRecording.backendId
      break
    }
  }
}

// Forward to backend if we now have backendId
if (backendId) {
  // ... existing forwarding logic
}
```

**Why this approach:** The race window is narrow (user must save dialog before audio upload completes), so a short retry is sufficient. No new infrastructure (queues, background jobs) needed. If all retries fail, the existing graceful degradation (files saved to disk) still applies.

### Pattern 3: Top-Level Import Cleanup (Tech Debt)

**What:** Move `import re` from line 263 inside `generate_diagram()` to the top of `document_generation.py` alongside other imports.

**Current state (line 263):**
```python
    # Strip markdown fences the LLM may add despite instructions
    import re
    raw = re.sub(r"^```\w*\n?", "", raw)
```

**Fix:** Add `import re` after `from typing import Any` at the top of the file, remove the function-level import.

### Anti-Patterns to Avoid
- **Do NOT add response_model=TranscriptResponse to the transcript endpoint** -- that is a future improvement, not part of this fix. The goal is to make the model READY for it, not to activate it.
- **Do NOT introduce background job infrastructure** for the document forwarding -- a simple retry is sufficient given the narrow race window.
- **Do NOT change the speaker update endpoint behavior** -- only the model definition needs updating.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic | Custom job queue | Simple for-loop with setTimeout | Race window is < 5 seconds, no need for infrastructure |
| Model validation | Custom dict checking | Pydantic default fields | Pydantic handles missing fields with defaults natively |

## Common Pitfalls

### Pitfall 1: Breaking Backward Compatibility with SpeakerStats
**What goes wrong:** Adding required fields (no default) to SpeakerStats would break deserialization of old stored data that lacks those fields.
**Why it happens:** Old transcripts stored before Phase 6 don't have custom_label/role in their speaker stats.
**How to avoid:** Always use defaults: `custom_label: str = ""` and `role: str = "Participant"`.
**Warning signs:** Any field added without a default value.

### Pitfall 2: Infinite Retry Loop in Documents Route
**What goes wrong:** Retry loop blocks the API response indefinitely.
**Why it happens:** Backend may be down, so backendId never appears.
**How to avoid:** Cap retries (5 attempts x 1s = 5 seconds max) and let graceful degradation handle failure.
**Warning signs:** No retry limit, no timeout.

### Pitfall 3: Documentation Checkboxes Out of Sync
**What goes wrong:** Marking checkboxes that don't match actual audit findings.
**How to avoid:** Cross-reference the v1.1-MILESTONE-AUDIT.md exactly. PLAY-02 was verified SATISFIED but its REQUIREMENTS.md checkbox was `[ ]`. Phase 5 and 6 plan checkboxes in ROADMAP.md are all `[ ]` despite being complete.
**Warning signs:** Not reading the audit report before making changes.

## Code Examples

### Current SpeakerStats Model (backend/models.py:33-45)
```python
class SpeakerStats(BaseModel):
    """Per-speaker statistics."""
    label: str
    talk_time_pct: float
    utterance_count: int
    talk_time: float
    word_count: int
    wpm: float
    turns: int
    avg_turn_duration: float
    pauses: int
    avg_pause_duration: float
    # MISSING: custom_label and role
```

### Backend Already Produces These Fields (transcription.py:459-460)
```python
speaker["custom_label"] = info.get("name", "")
speaker["role"] = info.get("role", "Participant")
```

### Current Race Condition (documents/route.ts:55)
```typescript
if (backendId) {
  // Only forwards if backendId already set
  // Skips silently if audio upload hasn't completed yet
}
```

### Timing Analysis of the Race
1. `RecordingFAB` fires `uploadRecording.mutate(formData)` -- async, background
2. Simultaneously opens `PostRecordingDialog`
3. `POST /api/recordings` saves file, creates DB record, then calls `fetch(BACKEND_URL/recordings)` synchronously
4. On backend response, sets `backendId` via `updateRecording`
5. User fills dialog fields and clicks Save
6. `POST /api/recordings/{id}/documents` checks `backendId` -- may be null if step 4 hasn't completed

The FAB's upload (`POST /api/recordings`) is async from the UI perspective but the backend call is awaited server-side before the route returns. The `uploadRecording.mutate` callback in React fires the request but doesn't block the dialog from opening. The dialog itself requires user interaction (typing a name, selecting project, dropping files, clicking Save), so there is typically enough time. But on fast saves with slow backends, the race is real.

### Function-Level Import (document_generation.py:263)
```python
def generate_diagram(...):
    ...
    import re  # Should be at module top
    raw = re.sub(r"^```\w*\n?", "", raw)
```

## State of the Art

No technology changes needed. This is a cleanup phase using existing patterns.

| Item | Current State | Target State |
|------|--------------|--------------|
| SpeakerStats model | Missing 2 fields, bypassed by raw dict return | All fields present, response_model-safe |
| Document forwarding | Conditional on backendId at upload time | Retries until backendId available |
| `import re` | Function-level in document_generation.py | Top-level import |
| REQUIREMENTS.md | PLAY-02 marked `[ ]` despite being satisfied | PLAY-02 marked `[x]` |
| ROADMAP.md | Phase 5/6 plan checkboxes `[ ]` | All complete plans marked `[x]` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pyproject.toml` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPKR-01/02 (INT-01) | SpeakerStats model accepts custom_label and role fields | unit | `cd backend && python -m pytest tests/test_models_speaker_stats.py -x` | No -- Wave 0 |
| RUX-02/DOC-02 (INT-02) | Documents forwarded when backendId delayed | integration | Manual -- requires running backend | N/A manual-only |
| GEN-02 | Document context available after delayed forwarding | integration | Manual -- end-to-end flow | N/A manual-only |
| DOC-02 (import fix) | No function-level imports in document_generation.py | unit/lint | `cd backend && python -c "import ast, sys; tree=ast.parse(open('document_generation.py').read()); sys.exit(any(isinstance(n,ast.Import) or isinstance(n,ast.ImportFrom) for node in ast.walk(tree) for n in [node] if hasattr(n,'col_offset') and n.col_offset > 0))"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_models_speaker_stats.py` -- unit test: SpeakerStats model with custom_label/role fields validates correctly, defaults work for backward compat
- [ ] Verify existing tests still pass after import move (no new test file needed)

## Open Questions

1. **Should the transcript endpoint add response_model=TranscriptResponse?**
   - What we know: The audit says "adding response_model would not drop data" is the success criterion
   - What's unclear: Whether to actually ADD it or just make the model ready for it
   - Recommendation: Only make the model ready (add fields). Adding response_model is a separate future change -- the success criterion says "would not drop data" (hypothetical), not "does not drop data" (actual).

2. **What if the backend is completely down during document upload?**
   - What we know: Retry will fail after 5 attempts, files remain on disk
   - What's unclear: Whether there should be a recovery mechanism for this case
   - Recommendation: Out of scope. Graceful degradation (files on disk) is acceptable. A recovery mechanism would be v1.2+ scope.

## Sources

### Primary (HIGH confidence)
- `backend/models.py` -- SpeakerStats model definition (lines 33-45)
- `backend/transcription.py` -- identify_speakers_with_llm sets custom_label/role (lines 459-460)
- `src/app/api/recordings/[id]/documents/route.ts` -- backendId null check (line 55)
- `src/components/recording/recording-fab.tsx` -- upload + dialog timing (lines 20-42)
- `src/app/api/recordings/route.ts` -- backendId set after backend response (line 68)
- `backend/document_generation.py` -- function-level import re (line 263)
- `.planning/v1.1-MILESTONE-AUDIT.md` -- all gap definitions and tech debt items

### Secondary (MEDIUM confidence)
- None needed -- all findings from direct code inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all existing code
- Architecture: HIGH - fixes are precisely scoped by the audit
- Pitfalls: HIGH - well-understood patterns (Pydantic defaults, retry logic)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- no external dependencies changing)

