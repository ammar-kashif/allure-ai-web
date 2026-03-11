# Domain Pitfalls

**Domain:** AI-powered meeting transcription and project plan extraction (local-first)
**Researched:** 2026-03-11
**Confidence:** MEDIUM (based on training data, web search unavailable for verification)

## Critical Pitfalls

Mistakes that cause rewrites, demo failures, or blown deadlines.

### Pitfall 1: Browser Audio Recording Silently Fails or Produces Unusable Audio

**What goes wrong:** The MediaRecorder API has inconsistent codec support across browsers. Chrome supports `audio/webm;codecs=opus`, Safari prefers `audio/mp4;codecs=aac`. Recording starts, appears to work, but the resulting file is either empty, corrupted, or in a format Whisper cannot ingest. Additionally, `getUserMedia` permission prompts can confuse users, and if the tab loses focus or the device sleeps, recording can silently stop or produce gaps.

**Why it happens:** Developers test recording in one browser, assume it works everywhere. MediaRecorder's `ondataavailable` event fires with Blob chunks, but the final concatenated file may lack proper headers if `stop()` is not called cleanly. Whisper expects specific audio formats (16kHz mono WAV ideally), and WebM/Opus output needs transcoding.

**Consequences:** Demo day: press record, get silence or a file Whisper rejects. Hours wasted debugging codec issues under deadline pressure.

**Prevention:**
- Hardcode to Chrome/Chromium for the FYP demo. Do not attempt cross-browser audio recording support in 2 weeks.
- Use `audio/webm;codecs=opus` as the MIME type, check `MediaRecorder.isTypeSupported()` at init and show a clear error if unsupported.
- Transcode to WAV (16kHz mono) server-side using ffmpeg before feeding to Whisper. The Python backend should handle this, not the frontend.
- Implement a "test recording" flow early: record 5 seconds, upload, transcribe, verify the full pipeline works end-to-end before building any UI polish.
- Save raw blobs to disk immediately via chunked upload, do not accumulate in browser memory.

**Detection:** Test the full record-to-transcript pipeline on day 1. If you cannot get a clean transcript from a browser recording within the first 2 days, this is a blocker.

**Phase:** Must be resolved in Phase 1 (core recording pipeline). This is the foundation everything else depends on.

---

### Pitfall 2: Whisper + Diarization Pipeline Takes Too Long for Demo Flow

**What goes wrong:** Whisper transcription on local hardware (even M3) takes significant time relative to audio length. A 30-minute meeting recording can take 5-15 minutes to transcribe with `whisper-large-v3`, and adding speaker diarization (e.g., pyannote.audio) adds another processing step. The "record and get a project plan in under 5 minutes" promise breaks for any non-trivial recording.

**Why it happens:** Teams test with 30-second clips during development. Everything feels fast. Then at demo time, a 10-minute recording takes 8 minutes to process and the audience loses patience.

**Consequences:** Demo feels broken. The core value prop ("meeting to plan in 5 minutes") is undermined. Worse, if the backend processes synchronously, the UI appears frozen.

**Prevention:**
- Use `whisper-base` or `whisper-small` for the FYP demo, not `whisper-large`. Accuracy difference is noticeable but speed difference is dramatic (10x+ faster). For a demo, speed matters more than perfect accuracy.
- Pre-record a demo meeting (2-3 minutes max) and pre-process it. Have the transcript ready as a fallback. Never rely on live processing for the primary demo path.
- Make transcription asynchronous with clear progress indication in the UI (status: "Processing", "Transcribing", "Extracting outcomes").
- Test with realistic-length recordings (5-10 minutes) early, not just 15-second clips.
- If diarization is slow, make it optional or fake it for demo (label all speakers as "Speaker 1" and show the diarization UI as a manual correction feature).

**Detection:** By day 3, you should have benchmarked: "A 5-minute recording takes X minutes to transcribe on our M3." If X > 3, switch to a smaller Whisper model or pre-process demo recordings.

**Phase:** Phase 1 (backend pipeline validation). Must benchmark before building the UI around it.

---

### Pitfall 3: Local LLM Output is Unreliable for Structured Extraction

**What goes wrong:** A quantized 7-8B parameter model (Llama 3.1 8B Q4_K_M, Mistral 7B) asked to extract structured JSON (decisions, action items, requirements, blockers) from transcript text produces: malformed JSON, hallucinated items not in the transcript, missed items that are clearly stated, inconsistent schema across runs, and confidence scores that are meaningless (always 0.85 or always random).

**Why it happens:** Small quantized models are significantly less reliable at instruction-following and structured output than GPT-4 or Claude. Developers prototype with a cloud API, get great results, then switch to local inference and are shocked at the quality drop. The model "sort of" follows the schema but breaks in subtle ways: missing closing braces, invented fields, action items that paraphrase rather than extract.

**Consequences:** The entire value chain after transcription depends on reliable extraction. If extraction is garbage, the confidence-gated review screen is useless, task generation is wrong, and the product is a toy.

**Prevention:**
- Use llama.cpp's grammar-constrained generation (GBNF grammars) to force valid JSON output. This eliminates malformed JSON entirely. Define the exact schema as a grammar.
- Keep prompts simple and few-shot. Include 2-3 examples of transcript-to-extraction in the prompt. Small models respond much better to examples than to complex instructions.
- Process transcripts in chunks (per-speaker-turn or per-5-minute-window), not as one giant prompt. Small context windows and attention degradation make whole-transcript processing unreliable.
- Make confidence scores rule-based rather than LLM-generated. The LLM extracts items; your code scores them based on heuristics (keyword matches, speaker agreement, repetition). LLM-generated confidence scores from small models are essentially random numbers.
- Have a hardcoded fallback demo transcript with pre-extracted outcomes. If live extraction fails at demo time, seamlessly show the pre-processed version.

**Detection:** By day 4-5, run 10 different transcript excerpts through your extraction pipeline. If more than 30% produce broken JSON or obviously wrong items (even with GBNF), the prompt needs rework or the model needs swapping.

**Phase:** Phase 1-2. Validate extraction quality immediately after STT pipeline is confirmed working.

---

### Pitfall 4: Scope Creep Kills the Demo Path

**What goes wrong:** With 16+ active requirements listed, the team spreads effort across features instead of nailing the core demo path: Record -> Transcribe -> Extract Outcomes -> Generate Tasks. Features like Kanban views, PRD generation, Mermaid diagrams, QA agent, and notification systems consume time that should go toward making the core path bulletproof.

**Why it happens:** FYP evaluation rewards breadth (or appears to). Team members want to work on "their" feature. It feels productive to build a Kanban board while waiting for the STT pipeline to be debugged. But a polished Kanban view with a broken recording pipeline is a failed demo.

**Consequences:** Demo day: 8 half-built features, none working end-to-end. The evaluator asks "show me the main flow" and it crashes.

**Prevention:**
- Define the demo script on day 1. Write the exact steps the evaluator will see. Everything not in that script is secondary.
- Week 1: core pipeline only (record, transcribe, extract, display). No UI polish, no secondary features.
- Week 2: polish the demo path, then and only then add secondary features if time permits.
- Track features as "demo path" vs "nice to have" and enforce the distinction in daily standups.
- PRD generation, Mermaid diagrams, QA agent, and notification system are all post-core-path features. Do not start them until the demo path works flawlessly.

**Detection:** If by day 5 you cannot demo the full Record -> Transcript -> Outcomes -> Tasks flow (even with ugly UI), you are behind. Drop all secondary features immediately.

**Phase:** All phases. This is a process discipline, not a technical fix.

---

### Pitfall 5: Frontend-Backend Integration Assumptions

**What goes wrong:** The frontend team builds against assumed API contracts. The Python backend (FastAPI) already exists with its own data models, endpoint patterns, and processing assumptions. When integration happens (often late), there are mismatches: different field names, different status enums, missing endpoints, unexpected async behavior, CORS issues, file upload format disagreements.

**Why it happens:** In a 2-week timeline, teams defer integration to "later" and build in parallel with mocked data. The mocks do not match reality. The existing backend was built without the frontend's needs in mind.

**Consequences:** Days 10-14 become an integration nightmare. Features that worked with mocked data break with real API responses. Time runs out before fixes are complete.

**Prevention:**
- Day 1: read the existing backend code. Document every endpoint, request/response shape, and status code. Do not assume -- read the actual FastAPI route definitions.
- Build a thin integration test on day 1-2: frontend calls real backend endpoint, gets real response, displays it. Even if ugly, this proves the integration path works.
- Use TypeScript types generated from or matching the actual backend response shapes. Do not invent frontend types and hope they match.
- If the backend needs new endpoints (e.g., for outcome extraction, task creation), define and build them in week 1, not week 2.
- CORS, authentication, and file upload (multipart/form-data for audio) are the three integration pain points. Solve all three on day 1-2 with minimal test cases.

**Detection:** If by day 3 the frontend has not successfully called at least one real backend endpoint and displayed the response, integration risk is high.

**Phase:** Phase 1. Integration before features.

## Moderate Pitfalls

### Pitfall 6: Audio File Size and Upload Handling

**What goes wrong:** A 30-minute meeting recording at reasonable quality (128kbps Opus) is ~28MB. Uploading this via a standard multipart form submission can timeout, fail silently, or consume excessive browser memory if the entire file is held in a Blob. The backend may reject large files if not configured for it (FastAPI/Starlette default upload limits).

**Prevention:**
- Set explicit file size limits in both frontend (pre-upload check) and backend (FastAPI `UploadFile` with configured max size).
- For the FYP, cap demo recordings at 5-10 minutes. This is a reasonable constraint that avoids file size issues entirely.
- Use chunked upload if recordings might exceed 50MB, but for FYP scope, a simple single POST with increased timeout is sufficient.
- Store files to `~/.allure/recordings/` on the backend immediately, return a file ID, process asynchronously.

**Detection:** Test with a 10-minute recording upload. If it fails or takes >10 seconds, investigate.

**Phase:** Phase 1 (recording pipeline).

---

### Pitfall 7: SQLite Concurrency Under Async FastAPI

**What goes wrong:** SQLite has a single-writer lock. FastAPI with async handlers can issue concurrent writes (e.g., updating transcript status while inserting extracted outcomes). This causes `database is locked` errors that appear intermittently and are hard to reproduce.

**Prevention:**
- Use WAL (Write-Ahead Logging) mode: `PRAGMA journal_mode=WAL;` -- this allows concurrent reads with a single writer and dramatically reduces lock contention.
- Serialize all write operations through a single async queue or use a connection pool size of 1 for writes.
- For FYP scale (single user, one recording at a time), this is unlikely to be a showstopper, but WAL mode should be enabled from day 1 as a safety net.

**Detection:** If you see intermittent `OperationalError: database is locked` in backend logs during testing, this is the cause.

**Phase:** Phase 1 (backend setup). One-line fix, but must be done early.

---

### Pitfall 8: Transcript-to-Outcome Mapping Loses Context

**What goes wrong:** The LLM extracts "Create login page" as an action item, but the evidence link points to a vague region of the transcript. When the user clicks the evidence link to verify, they see a 30-second window of conversation that does not clearly support the extracted item. The confidence-gating feature becomes useless if evidence links are imprecise.

**Prevention:**
- Extract outcomes at the utterance level, not the document level. Feed individual speaker turns or small groups of turns to the LLM, and tag each extraction with the exact utterance IDs it came from.
- Store transcript as an array of timestamped utterances, not a single text blob. Each outcome links to specific utterance indices.
- For the FYP demo, even approximate evidence linking (within 60 seconds of the relevant discussion) is acceptable. Do not over-engineer precise linking.

**Detection:** After extraction, manually check 5 outcomes: does clicking the evidence link show relevant context? If 3+ are wrong, the chunking strategy needs adjustment.

**Phase:** Phase 2 (outcome extraction and review).

---

### Pitfall 9: Overengineering the Review/Approval UI

**What goes wrong:** The confidence-gated review screen becomes a complex approval workflow with inline editing, bulk actions, confidence threshold adjustment, evidence preview, and side-by-side comparison. This consumes a week of frontend time for a feature that, in the demo, will be used once on 5-10 items.

**Prevention:**
- The review screen is a simple list: item text, confidence badge, evidence link, approve/reject buttons. That is it.
- No inline editing in v1. If an item is wrong, reject it. The demo does not need edit-and-resubmit flows.
- Bulk approve (select all above 0.80) is the only "power feature" worth building.
- Spend at most 1 day on this screen.

**Detection:** If the review screen spec has more than 5 interactive elements per item, it is overscoped.

**Phase:** Phase 2 (review UI). Timebox strictly.

---

### Pitfall 10: llama.cpp Setup and Model Loading Issues on Demo Day

**What goes wrong:** llama.cpp works on the developer's machine but fails on the demo machine. Model file path is hardcoded. Metal/GPU acceleration is not available or not enabled. The model file (4-8GB for quantized 7B) is missing or corrupted. First inference after model load takes 30+ seconds (cold start).

**Prevention:**
- Make model path configurable via environment variable, not hardcoded.
- Pre-warm the model on demo machine startup: send a dummy inference request at application start so the model is loaded into memory before the demo begins.
- Test on the exact demo machine at least 1 day before the demo. Do not assume "it works on my machine" transfers.
- Keep a copy of the model file on a USB drive as backup.
- If llama.cpp setup proves fragile, fall back to Ollama (which wraps llama.cpp but handles model management). The project noted llama.cpp over Ollama, but a working Ollama demo beats a broken llama.cpp demo.

**Detection:** Set up a fresh machine test on day 10-11. If it takes more than 30 minutes to get inference working, switch to Ollama.

**Phase:** Phase 1 (infrastructure). Validate on day 1.

## Minor Pitfalls

### Pitfall 11: Audio Playback Sync with Transcript

**What goes wrong:** Click-to-seek (click utterance, audio jumps to that timestamp) sounds simple but timestamp alignment between Whisper output and the audio player can drift, especially if the audio was transcoded or trimmed. The HTML5 `<audio>` element's `currentTime` property works in seconds with float precision, but Whisper timestamps may have slight offsets.

**Prevention:**
- Accept +/- 1 second drift as good enough for FYP. Do not spend time on sub-second alignment.
- Use the Whisper segment timestamps directly (they are in seconds already). Map each utterance to `segment.start`.
- Test with a recording where you say timestamps out loud ("it is now 30 seconds") to verify alignment.

**Phase:** Phase 2 (transcript editor). Low priority relative to core pipeline.

---

### Pitfall 12: Next.js SSR Complications for a Local-First App

**What goes wrong:** Next.js defaults to server-side rendering, which adds complexity for a local-first app that primarily needs client-side interactivity (audio recording, real-time UI updates, local state). Developers fight hydration mismatches, `window is not defined` errors, and unnecessary SSR for pages that are entirely client-interactive.

**Prevention:**
- Use `'use client'` liberally. This is a client-heavy application. Almost every page component will need client-side rendering.
- Do not use server components for recording, playback, or any interactive feature. Reserve server components for initial data fetching/layout only.
- If SSR causes more problems than it solves, consider using Next.js purely as a SPA (all pages client-rendered). For an FYP with no SEO requirements, this is perfectly fine.

**Phase:** Phase 1 (project setup). Decide the SSR strategy on day 1 and stick with it.

---

### Pitfall 13: Git Workflow Overhead for a 2-Person Team

**What goes wrong:** Setting up elaborate branching strategies, PR reviews, and CI/CD pipelines consumes time better spent coding. Alternatively, no coordination leads to merge conflicts on shared files.

**Prevention:**
- Simple rule: each person owns specific files/features. Communicate before touching someone else's code.
- Use a single `main` branch with direct pushes, or at most feature branches with fast-forward merges. No PRs for a 2-week FYP.
- Commit frequently (every working feature, every hour of progress). This is your undo mechanism.

**Phase:** Day 1 decision. Not worth revisiting.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Recording pipeline (Phase 1) | Browser audio format incompatible with Whisper | Transcode server-side with ffmpeg, test end-to-end on day 1 |
| Recording pipeline (Phase 1) | Audio upload fails silently for large files | Set explicit size limits, test with 10-min recording |
| STT integration (Phase 1) | Whisper processing time too slow for demo | Benchmark on day 2, use whisper-small/base, pre-process demo recording |
| Backend integration (Phase 1) | API contract mismatches discovered late | Read backend code on day 1, build integration test on day 2 |
| LLM extraction (Phase 1-2) | Malformed JSON output from local model | Use GBNF grammar constraints in llama.cpp, few-shot prompts |
| LLM extraction (Phase 1-2) | Hallucinated outcomes not in transcript | Chunk transcripts, include source utterances in prompt, manual QA |
| Outcome review UI (Phase 2) | Overengineered approval workflow | Timebox to 1 day, simple list with approve/reject only |
| Task generation (Phase 2) | LLM generates vague/unhelpful tasks | Provide structured outcome data as input, not raw transcript |
| Demo preparation (Phase 3) | Live processing fails under pressure | Pre-process demo recording, have fallback data ready |
| Demo preparation (Phase 3) | llama.cpp fails on demo machine | Test on exact demo hardware day 10-11, Ollama as fallback |
| Feature breadth (All phases) | Scope creep beyond core demo path | Write demo script on day 1, enforce core-path-first discipline |

## FYP-Specific Meta-Pitfall: The "But We Need More Features" Trap

FYP evaluators care about:
1. Does the core concept work end-to-end? (60% of impression)
2. Is it polished where it matters? (25%)
3. Is there breadth? (15%)

Teams consistently over-index on breadth and under-index on "does it actually work." A demo where recording -> transcription -> extraction -> tasks works flawlessly with a clean UI will score higher than one with Kanban boards, PRD generation, Mermaid diagrams, and a notification system where the core recording pipeline crashes.

**The priority stack for 2 weeks:**
1. Days 1-4: Core pipeline works end-to-end (record, upload, transcribe, extract, display)
2. Days 5-8: Polish the demo path UI, fix edge cases, build review/approve/promote-to-tasks flow
3. Days 9-10: Secondary features (Kanban, task management views) only if core path is solid
4. Days 11-12: Demo preparation, fallback data, practice run on demo hardware
5. Days 13-14: Buffer for fires. There will be fires.

## Sources

- Training data knowledge of MediaRecorder API, Whisper, llama.cpp, FastAPI, SQLite, Next.js (MEDIUM confidence -- web search unavailable for verification)
- Project context from `.planning/PROJECT.md`
- Note: All findings are based on training data (cutoff ~May 2025). Specific version behaviors of Whisper, llama.cpp, and pyannote may have changed. Recommend verifying llama.cpp GBNF grammar support and current Whisper model speed benchmarks on your specific hardware.
