# Project Research Summary

**Project:** Allure AI v1.1 — Meeting Intelligence & Document Context
**Domain:** AI-powered meeting intelligence (audio playback sync, speaker analytics, document context injection, product-focused diagram generation)
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

Allure AI v1.1 adds six interconnected capabilities to a validated v1.0 meeting transcription stack: audio playback with transcript sync, enriched speaker analytics, editable speaker labels, a post-recording metadata popup, document attachment and context injection, and product-focused diagram generation via prompt rewriting. The existing architecture (Next.js 15 + FastAPI + dual SQLite + Zustand + TanStack Query) handles all of these additions with minimal new dependencies — only two new Python packages are required (`pymupdf`, `python-docx`). All new frontend state follows the established Zustand store pattern and all backend compute derives from existing utterance data without new models or data sources.

The recommended build order flows from infrastructure to UI to polish: start with the `AgglomerativeClustering` swap and audio playback store (both independent, high-risk areas that need early validation), then add the speaker stats display and transcript sync UI, then handle the UX flow change for the post-recording popup and speaker label editing, then add document attachment infrastructure, and finally wire document context into generation prompts and rewrite those prompts for product focus. This order surfaces the highest-risk items first — threshold tuning for clustering, WebM seek compatibility for audio — before layering dependent features on top.

The most dangerous pitfalls are architectural rather than algorithmic: the dual-database split between frontend and backend SQLite requires an explicit contract for how document parsed text reaches the generation endpoints; the 4096-token context window must be expanded to 8192 before document context injection is implemented; and speaker turn statistics must be computed before the segment merge step or the turn/pause metrics will be systematically wrong. Each of these is a rewrite-forcing mistake if discovered late. The prompt quality pitfall — LLMs diagramming the meeting discussion instead of the product — is the most likely demo failure point and requires iterative testing before shipping.

## Key Findings

### Recommended Stack

The v1.0 stack is unchanged and continues to carry all new features. Only two Python packages are added: `pymupdf>=1.27` for PDF text extraction (3-5x faster than pypdf with better complex layout handling) and `python-docx>=1.1` for DOCX parsing. Audio playback uses the native HTML5 `<audio>` element via React ref — no audio library needed. Speaker statistics use pure Python arithmetic over existing segment data. `AgglomerativeClustering` is already available in the installed scikit-learn (>=1.5). Audio file serving uses FastAPI's built-in `FileResponse`. Document context injection is prompt string concatenation within the existing `document_generation.py`. See `.planning/research/STACK.md` for full detail and alternatives considered.

**Core technologies added:**
- `pymupdf>=1.27`: PDF text extraction — fastest Python extractor, handles complex layouts, wheels ship with C dependencies
- `python-docx>=1.1`: DOCX parsing — standard library, deterministic paragraph/table extraction
- `sklearn.cluster.AgglomerativeClustering`: diarization clustering upgrade — zero new dependency, standard approach for ECAPA-TDNN cosine embeddings
- Native HTML5 `<audio>` + React refs: audio playback and sync — no library overhead, full seeking/timeupdate API, serves WAV for cross-browser seek compatibility
- FastAPI `FileResponse`: audio file serving — already in FastAPI, handles range requests for browser seeking

### Expected Features

The feature set is concrete and well-scoped. Research confirms each item's implementation pattern with high confidence. See `.planning/research/FEATURES.md` for complexity budgets and dependency graph.

**Must have (table stakes):**
- Audio playback with click-to-seek — every competitive transcript tool (Otter, Fireflies, Fathom) has this; missing it makes the transcript page feel static
- Active utterance highlight during playback — standard visual affordance, users expect it
- Editable speaker labels — "Speaker 1" is unusable in meeting minutes; renaming is essential for credibility
- Per-speaker talk time statistics — "who talked the most" is the first question after any meeting; data already computed backend-side
- Post-recording popup (title, project, doc upload) — current auto-save flow gives no chance to name a recording or attach context docs

**Should have (competitive differentiators):**
- Document context injection into PRD/diagram generation — "upload your existing spec and get a grounded PRD" is the FYP demo moment
- Product-focused diagram generation — diagrams that model the product discussed, not the meeting discussion flow
- Extended speaker statistics (WPM, turns, pauses) — Fireflies-level analytics; all computable from existing utterance data
- AgglomerativeClustering upgrade — more reliable speaker count detection; invisible in demo but reduces diarization failures
- Improved Mermaid syntax validation and retry — reduces blank diagram failures from small-LLM syntax errors
- Speaker roles (PM, Engineer, Designer) — extends editable labels; minimal extra effort

**Defer (v2+):**
- Real-time live transcription during recording — requires streaming STT and WebSocket infrastructure; years to polish
- Vector embedding / semantic search over documents — full RAG pipeline adds infrastructure complexity with no benefit at this document scale
- Speaker identification across recordings — requires speaker enrollment and voice print matching
- Audio waveform visualization — visually appealing but no functional value beyond the transcript-centric UX
- AI chat interface for meeting content — out of scope; FYP demonstrates structured workflows, not open-ended chat
- Drag-and-drop document priority reordering — over-engineering at this scale

### Architecture Approach

The v1.1 architecture extends three established patterns from v1.0. All backend calls remain proxied through Next.js API routes. All cross-component reactive state uses Zustand stores (a new `PlaybackStore` mirrors the existing `EvidenceHighlightStore` pattern). UI-only data (speaker labels, roles) stays in frontend SQLite without backend round-trips. The critical new decision is the dual-database data contract: document files and parsed text are owned by the backend after upload, and the frontend sends document context to generation endpoints as part of request bodies — the backend never reads from the frontend DB. See `.planning/research/ARCHITECTURE.md` for full component map, data flow diagrams, and build order.

**Major components (new/modified):**
1. `PlaybackStore` (Zustand) — source of truth for `currentTime`, `isPlaying`, `seekTo`; coordinates `AudioPlayer`, `TranscriptView`, and `UtteranceBubble`
2. `AudioPlayer` — HTML5 `<audio>` wrapper using rAF-throttled polling (~10Hz) for active-segment detection; emits seek commands via store; serves WAV from backend
3. `PostRecordingPopup` — dialog after recording stop; audio uploads immediately on stop, popup updates metadata (title, project, documents) via PATCH requests
4. Document attachment pipeline — multipart upload frontend to backend; backend owns PyMuPDF/python-docx parsing, stores extracted text per job; frontend stores metadata only
5. `FastDiarizer` (modified) — `AgglomerativeClustering(distance_threshold=0.7, metric="cosine", linkage="average")` replaces `MeanShift`; stats computed pre-merge
6. `document_generation.py` (modified) — rewritten prompts with explicit product-focus instructions, negative examples, and document context prepended before outcomes; `n_ctx` increased to 8192
7. `SpeakerStatsPanel` + `MeetingStatsCard` — render enriched stats from existing transcript response shape (no new endpoints)

### Critical Pitfalls

The full pitfall catalogue (13 items) is in `.planning/research/PITFALLS.md`. The top five with architectural implications:

1. **`timeupdate` lag makes transcript sync feel broken** — Use `requestAnimationFrame` polling throttled to ~10Hz when audio is playing; fall back to `timeupdate` only when tab is backgrounded. Binary search segment array for active-segment detection. This is architectural — retrofitting from `timeupdate` to rAF later requires rewriting the entire sync loop.

2. **AgglomerativeClustering threshold/linkage misconfiguration causes wrong speaker counts** — `n_clusters` and `distance_threshold` are mutually exclusive in sklearn; cosine distances range 0-2 (not -1 to 1); `linkage="ward"` raises an error with cosine metric. Use `distance_threshold=0.7`, `linkage="average"`, validate against MeanShift on 5+ test recordings before swapping in production.

3. **Document context overflows the 4096-token context window** — `n_ctx=4096` in `main.py` is the total window for input AND output combined; any realistic attached document will overflow it. Increase `n_ctx` to 8192 before implementing context injection. Implement token budget: reserve ~1500 tokens for system prompt, ~1500 for outcomes, cap document context at remainder.

4. **LLM diagrams model the meeting, not the product** — Existing prompts say "generate from meeting outcomes" which biases the LLM toward diagramming the discussion flow. Two-phase prompt approach: first extract "what product/system is being discussed," then generate a diagram of that product. Add explicit negative instructions ("do NOT include speaker names, meeting actions, discussion steps"). Test by checking if diagram nodes contain words like "discussed," "proposed," or "Speaker."

5. **Speaker turn statistics computed post-merge give wrong results** — `merge_consecutive_segments` collapses consecutive same-speaker segments before `calculate_speaker_stats` runs (confirmed at `transcription.py` lines 257-314). Turn counts, avg turn duration, and pause detection must be computed from pre-merge aligned segments. Coordinate this with the AgglomerativeClustering change to avoid double-refactoring the transcription pipeline.

## Implications for Roadmap

Based on research, the dependency graph and pitfall phase-warnings suggest five phases:

### Phase 1: Foundation — Clustering Upgrade & Playback Store
**Rationale:** AgglomerativeClustering and the PlaybackStore are the two highest-risk items and have zero dependencies on other v1.1 features. Getting them right first means the rest of the milestone builds on a stable foundation. Both are isolated changes (backend-only / frontend store-only) with no API surface changes needed.
**Delivers:** Improved diarization reliability; Zustand PlaybackStore wired and ready for UI consumption.
**Addresses:** AgglomerativeClustering differentiator (FEATURES.md); PlaybackStore prerequisite for all audio sync UI.
**Avoids:** Pitfall 2 (clustering misconfiguration), Pitfall 12 (rAF battery drain — throttle configured from day one).

### Phase 2: Audio Playback & Speaker Analytics
**Rationale:** PlaybackStore from Phase 1 unblocks this phase. Speaker stats enrichment is a backend-only computation change with no new endpoints, and its frontend rendering (`SpeakerStatsPanel`, `MeetingStatsCard`) is straightforward. Audio playback sync is the headline table-stakes feature — it transforms a static transcript page into an interactive meeting review experience and should be visible as early as possible.
**Delivers:** Click-to-seek, active utterance highlight during playback, enriched per-speaker stats display, meeting stats overview card.
**Addresses:** Audio playback (table stakes), per-speaker statistics (table stakes), extended statistics (differentiator).
**Avoids:** Pitfall 1 (timeupdate lag — use rAF polling), Pitfall 6 (stats computed post-merge — compute before merge), Pitfall 7 (WebM seek on Safari — serve WAV from backend endpoint), Pitfall 13 (overlapping window duration overcounting — use librosa audio duration for meeting-level stats).

### Phase 3: Speaker Label Editing & Recording UX
**Rationale:** These two features (editable speaker labels, post-recording popup) are independent of document attachments and audio sync. The popup gates document upload and must precede Phase 4. Speaker label editing is frontend-only CRUD (new `speaker_labels` SQLite table) and ships alongside the popup naturally.
**Delivers:** Editable speaker names and roles; post-recording popup with title, project assignment, and doc upload drop zone; audio uploads immediately on stop with popup patching metadata.
**Addresses:** Editable speaker labels (table stakes), post-recording popup (table stakes), speaker roles (differentiator).
**Avoids:** Pitfall 9 (popup blocking upload pipeline — upload immediately, popup PATCH metadata after), Pitfall 10 (speaker labels invisible to backend — send label mapping with generation requests).

### Phase 4: Document Attachments Infrastructure
**Rationale:** The post-recording popup from Phase 3 is the primary upload entry point. The dual-database data contract (backend owns parsed text, frontend sends it with generation requests) must be established before any context injection is attempted. This phase has the most new infrastructure: two new endpoints (frontend + backend mirror), two new DB tables, file storage, and Python text extraction.
**Delivers:** Document upload via popup and recording detail page; PDF/DOCX/TXT parsing via PyMuPDF and python-docx; extracted text stored per job in backend; document list displayed in UI.
**Addresses:** Document attachments (table stakes).
**Avoids:** Pitfall 3 (token overflow — increase `n_ctx` to 8192 in this phase, before injection wiring), Pitfall 5 (silent parse failures — validate extracted text length, reject with clear user-facing error), Pitfall 8 (dual-DB inconsistency — backend owns parsed text from upload forward).

### Phase 5: Context-Aware Generation & Prompt Quality
**Rationale:** Document context injection requires Phase 4 infrastructure (parsed text available per job). Prompt rewrites for product-focused diagrams are independent but logically grouped here since document context makes the prompts more effective. Mermaid syntax validation is a quality improvement with no dependencies. This phase is prompt engineering plus thin code changes — lowest risk, but requires iterative testing with real recordings.
**Delivers:** PRD and diagram generation uses attached document text as primary context; diagrams model the product discussed, not the meeting flow; Mermaid syntax errors auto-corrected before display; raw-code fallback view for manual fixes.
**Addresses:** Document context injection (differentiator), product-focused diagrams (differentiator), Mermaid reliability (differentiator).
**Avoids:** Pitfall 3 (token overflow — token budget enforced), Pitfall 4 (LLM diagrams meeting flow — two-phase prompt with explicit negative instructions).

### Phase Ordering Rationale

- Foundation first because AgglomerativeClustering failures cascade through speaker stats, transcript display, and evidence refs — detecting this early is critical and the fix is isolated.
- Audio sync before document features because it is the most visible table-stakes gap; its PlaybackStore is self-contained and should be exercised early.
- Speaker stats alongside audio because the backend enrichment and frontend display are low-risk extensions of existing data with no new dependencies.
- Popup before document upload because the popup is the upload entry point; building upload without the popup creates dead-end UX.
- Document infrastructure before context injection because context injection has no value without parsed text available; and `n_ctx` must be expanded in Phase 4, not Phase 5.
- Prompt engineering last because it is iterative by nature, low risk, and benefits from having document context in place for realistic testing.

### Research Flags

Phases requiring careful implementation (no additional pre-planning research needed, but plan for iteration):
- **Phase 1 (AgglomerativeClustering):** Requires empirical threshold tuning on 3-5 real recordings with known speaker counts. The algorithm and starting values are confirmed — plan for 1-2 calibration iterations, not additional research.
- **Phase 2 (WebM/WAV seek compatibility):** Safari seek behavior needs hands-on testing. Research confirms the risk exists (MEDIUM confidence) but current Safari versions may have improved. Test on Safari before committing to WAV-serving approach.
- **Phase 5 (Prompt quality):** Prompt rewriting is inherently iterative. Plan for 2-3 rounds of prompt testing with real recordings. No amount of pre-research eliminates this iteration cycle.

Phases with standard, well-documented patterns (skip additional research):
- **Phase 2 (rAF sync loop):** HTML5 Audio API + rAF throttling is thoroughly documented. Implementation is mechanical once PlaybackStore is wired.
- **Phase 3 (Speaker label editing):** Frontend-only CRUD against SQLite, following the same patterns already in the codebase.
- **Phase 4 (Document upload/parsing):** PyMuPDF and python-docx are well-documented; the multipart upload pattern follows the existing audio upload code.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against current documentation; only 2 new dependencies; alternatives explicitly benchmarked and ruled out |
| Features | HIGH | Feature set directly researched against competitive tools (Otter, Fireflies, Fathom); implementation patterns confirmed against live v1.0 codebase |
| Architecture | HIGH | Based on direct code reading of v1.0 codebase (commit a7c2a34); all patterns verified against live files including transcription.py lines cited |
| Pitfalls | HIGH | 10 of 13 pitfalls confirmed by direct codebase reading; 2 confirmed via MDN/browser documentation; 1 (Safari WebM) is MEDIUM due to evolving browser support |

**Overall confidence:** HIGH

### Gaps to Address

- **AgglomerativeClustering `distance_threshold` value:** Start at 0.7 (well-tested starting point for ECAPA-TDNN cosine) but treat as a calibration task. The correct value for this specific audio environment can only be determined empirically. Flag a calibration step in Phase 1 with 3-5 test recordings.
- **Safari WebM seek behavior in 2026:** Research confirms historical issues. Serve WAV as the default-safe playback format. Revisit only if WAV file sizes become problematic (16kHz mono WAV ≈ 1.9MB/min, so 30-min recording ≈ 57MB).
- **Phi-4-mini diagram generation quality with improved prompts:** The LLM's ability to produce product-focused Mermaid from meeting outcomes needs empirical validation. Plan prompt iteration cycles in Phase 5 with real recordings, not synthetic inputs.
- **`n_ctx` increase latency impact on M3:** Phi-4-mini at 8192 context has not been benchmarked in this environment. If inference time increases unacceptably, smart document truncation (headings + first paragraphs) becomes the primary mitigation strategy over larger context windows.

## Sources

### Primary (HIGH confidence)
- PyMuPDF PyPI v1.27.2 — installation, extraction API
- python-docx PyPI v1.2.0 — version, Python support
- scikit-learn AgglomerativeClustering docs — distance_threshold API, cosine metric, linkage options, mutual exclusion constraint
- MDN: HTMLMediaElement timeupdate event — event frequency, precision behavior
- MDN: HTMLMediaElement currentTime — seeking behavior
- SpeechBrain spkrec-ecapa-voxceleb model card — embedding dimensions, diarization patterns
- Allure AI codebase direct read (commit a7c2a34) — `transcription.py`, `document_generation.py`, `storage.py`, `schema.sql`, `src/lib/db/index.ts`, `backend/main.py`

### Secondary (MEDIUM confidence)
- Otter vs Fireflies vs Fathom comparison (2025, 2026) — table stakes feature expectations
- SpeechBrain diarization processing docs — AgglomerativeClustering with speaker embeddings
- Metaview: Syncing a Transcript with Audio in React — React transcript sync patterns
- Simple Speaker Diarization with SpeechBrain (HuggingFace blog) — cosine threshold starting points for ECAPA-TDNN
- 2025/2026 Python PDF extractor comparisons — PyMuPDF performance benchmarks vs pypdf/pdfplumber
- GenAIScript Mermaids Unbroken — Mermaid syntax fix strategies for LLM output
- sklearn issue #27434 — distance_threshold + cosine metric behavior confirmation

### Tertiary (LOW confidence)
- Firefox bug 587465: audio.currentTime low precision — historical, behavior may have improved in current versions
- Safari WebM seek compatibility — historically confirmed, 2026 status needs hands-on validation
- MermaidSeqBench NeurIPS 2025 — LLM Mermaid generation quality benchmarks (Phi-4-mini not specifically tested)

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*

