# Feature Landscape

**Domain:** AI-powered meeting intelligence (audio playback sync, speaker analytics, document context injection, product-focused diagram generation)
**Researched:** 2026-03-18
**Milestone:** v1.1 Meeting Intelligence & Document Context

## Table Stakes

Features users expect in a meeting intelligence tool. Missing = product feels incomplete for v1.1 demo.

| Feature | Why Expected | Complexity | Dependencies on Existing | Notes |
|---------|--------------|------------|--------------------------|-------|
| Audio playback with click-to-seek | Every transcript tool (Otter, Fireflies, Fathom) has this. Users see timestamps on utterances and expect to click and hear that moment. | Medium | Utterances already have `startTime`/`endTime`; `TranscriptView` and `UtteranceBubble` exist. Audio file stored on filesystem via `filePath`. | HTML5 `<audio>` element with `currentTime` seeking. No external library needed. |
| Active utterance highlight during playback | Standard pattern in all transcript players. As audio plays, the currently-spoken utterance should visually highlight and auto-scroll into view. | Medium | `useEvidenceHighlight` store already handles highlight + scroll-into-view for evidence cross-navigation. Same pattern extends to playback highlighting. | Use `timeupdate` event (~4x/sec) to match `currentTime` against utterance time ranges. Consider a dedicated playback store separate from evidence highlight to avoid conflicts. |
| Click utterance to seek audio | Bidirectional sync: clicking a transcript line seeks the audio to that timestamp. | Low | `UtteranceBubble` already renders `startTime`. Just wire `onClick` to set audio `currentTime`. | Wire `onClick` on each bubble. Trivial once the audio element ref is accessible via context or store. |
| Editable speaker labels | Users need to replace "Speaker 1" with actual names (e.g., "Ahmed", "Product Lead"). Critical for meeting minutes credibility. | Medium | `Utterance` type has `speaker: string`. Backend stores speakers in transcript result. Frontend SQLite stores transcript. | Store a speaker mapping object `{ "Speaker 1": "Ahmed" }` at recording level rather than mutating every utterance. Apply mapping at render time. |
| Per-speaker talk time statistics | Basic expectation for any diarization-capable tool. "Who talked the most?" is the first question after any meeting. | Low | Backend `calculate_speaker_stats` already returns `talk_time_pct` and `utterance_count` per speaker. Data already flows to frontend in transcript response. | Just render the data that already exists. Stat cards or horizontal bar chart. |
| Post-recording popup (name, project, doc upload) | Current flow silently saves recording with auto-title. Users need a chance to name it, assign project, and attach docs before processing starts. | Medium | `useRecordingStore` tracks recording lifecycle. Recording creation and project assignment already exist via `project-assignment.tsx`. | Modal/dialog on recording stop. Processing starts in background immediately; popup collects metadata in parallel. |
| Document attachments on recordings | Users need to upload reference docs (specs, designs, prior PRDs) that provide context for AI generation. | Medium | Backend `uploads` directory exists. Frontend has file upload patterns (`upload-button.tsx`). Document generation endpoints exist but take no external context yet. | File upload (PDF/TXT/MD), store metadata in SQLite, store file on filesystem. Extract text content for context injection. |

## Differentiators

Features that set Allure apart from generic transcript tools. Not expected, but add significant demo value for FYP.

| Feature | Value Proposition | Complexity | Dependencies on Existing | Notes |
|---------|-------------------|------------|--------------------------|-------|
| Document context injection into PRD/diagram generation | Most tools generate from transcript only. Allure can incorporate uploaded reference docs (prior specs, requirements) to produce more grounded, product-relevant output. | Medium | `generate_prd` and `generate_diagram` in `document_generation.py` currently format only outcomes for the LLM prompt. Adding document text to the prompt context is straightforward. | Concatenate extracted document text into the LLM prompt alongside outcomes. Keep within 4096 token context window (Phi-4-mini). Truncate/summarize long docs proportionally. No vector DB needed -- simple context window stuffing. |
| Product-focused diagram generation | Current prompts produce diagrams that model the meeting flow (who said what, what was discussed). v1.1 should model the product being discussed (user flows of the app, ERD of the system). | Medium | `USERFLOW_SYSTEM_PROMPT` and `ERD_SYSTEM_PROMPT` exist in `document_generation.py`. Prompt wording focuses on "meeting outcomes" -- needs rewrite to extract the product/system being discussed and diagram its architecture. | Rewrite prompts to instruct LLM: "Extract the product/system described in these outcomes and diagram its user flows / data model." Add few-shot examples showing product-focused output. Iterative quality tuning needed. |
| Speaker roles (PM, Engineer, Designer) | Tagging speakers with roles helps the AI weight contributions differently and makes meeting minutes more professional. | Low | Extends the editable speaker labels feature. Store role alongside label in the speaker mapping. | Add role dropdown or tag alongside speaker name edit. Optionally pass roles to extraction prompts for better outcome attribution. |
| Extended speaker statistics (WPM, turns, avg turn length, pauses) | Goes beyond basic talk-time to provide genuine conversation analytics (Fireflies-level). | Medium | Backend `calculate_speaker_stats` returns basic stats. Utterance data has timing + text for all needed calculations. | All computable from existing utterance data: word count / duration = WPM, count speaker changes = turns, gap between consecutive same-speaker segments = pause duration. Pure computation, no new data sources needed. |
| Meeting-level statistics (duration, processing time, speaker count, attached docs count) | Overview card on recording detail gives quick context at a glance. | Low | Recording already has `durationMs`, transcript has `speakers` array. Processing time calculable from job timestamps. | Render in the existing "Info" tab. Replace the sparse info grid with a stat card layout. |
| AgglomerativeClustering for diarization | Current MeanShift can over-segment or under-segment. AgglomerativeClustering with cosine distance threshold is the standard approach in research papers using ECAPA-TDNN embeddings, giving more predictable speaker counts. | Medium | `FastDiarizer` uses `MeanShift` from sklearn. Drop-in replacement with `AgglomerativeClustering(n_clusters=None, distance_threshold=T, metric='cosine', linkage='average')`. Same embedding pipeline. | Requires tuning `distance_threshold` (typically 0.3-0.7 for ECAPA-TDNN cosine distances). Spectral clustering showed 37-38% DER improvement over x-vectors in published results. Test with sample recordings. |
| Improved Mermaid syntax reliability | Current generation sometimes produces invalid Mermaid that fails to render. Post-processing and validation can catch this. | Low | `MermaidDiagram` component renders Mermaid client-side. Backend returns raw LLM output. | Add validation step: attempt parse with mermaid.js before accepting. If invalid, auto-fix common issues (strip markdown fences, remove unsupported characters in labels) or retry generation once. |

## Anti-Features

Features to explicitly NOT build for v1.1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time live transcription display during recording | Massively complex (streaming STT, WebSocket, partial results). Over-engineering for FYP. Otter took years to polish this. | Keep current flow: record, then process. Post-recording popup makes the wait feel intentional. |
| Vector embedding / semantic search over documents | Full RAG with embeddings, chunking, vector DB is overkill. Allure's attached docs are small enough for full-text context window injection. Adding a vector DB (FAISS, ChromaDB) adds infrastructure complexity with no benefit at this scale. | Simple text extraction from uploaded docs, concatenate into LLM prompt. No vector DB. |
| Multi-format diagram gallery (sequence, class, state, Gantt, etc.) | User flow + ERD covers 90% of meeting-derived product diagrams. More types = more prompt engineering with diminishing returns. | Stick with flowchart TD + erDiagram. Sequence diagrams only if specific user demand emerges. |
| AI chat interface for querying meeting content | Conversational UI adds massive complexity and is generic. FYP should demonstrate structured workflows, not open-ended chat. Already in project Out of Scope. | Keep structured outcome extraction + document generation. |
| Speaker identification across recordings | Recognizing "this is Ahmed's voice" across multiple recordings needs speaker enrollment, embedding storage, voice print matching pipeline. | Per-recording speaker labels only. Users rename speakers manually per recording. |
| Audio waveform visualization | Visually appealing but adds complexity (Web Audio API spectrum analysis, canvas rendering) with minimal functional value beyond aesthetics. | Simple playback controls (play/pause, seek bar, time display) are sufficient. Focus on transcript sync, not audio visualization. |
| Drag-and-drop document reordering for context priority | Over-engineering the document attachment feature. Users don't need to prioritize which docs matter more at this scale. | All attached docs contribute equally to context. Truncate proportionally if total exceeds token budget. |

## Feature Dependencies

```
Audio Playback (new) ---------> Click-to-Seek (requires audio element)
                    \---------> Active Utterance Highlight (requires playback time tracking)

Editable Speaker Labels ------> Speaker Roles (roles extend the label editing UI)
                        \-----> Extended Speaker Statistics (stats use custom labels for display)

Post-Recording Popup ---------> Document Attachments (popup is primary upload entry point)

Document Attachments ---------> Context Injection into Generation (injection requires stored doc text)

Context Injection ------------> Product-Focused Diagrams (better context = better product modeling)
Prompt Rewrites --------------> Product-Focused Diagrams (quality depends on prompt quality)

AgglomerativeClustering ------> (independent, backend-only change, no frontend deps)
Improved Mermaid Syntax ------> (independent, frontend validation layer)
Meeting-Level Stats ----------> (independent, renders existing data)
```

## MVP Recommendation

Prioritize for maximum demo impact with minimum complexity:

1. **Audio playback with transcript sync** (click-to-seek + active highlight) -- THE table-stakes feature that transforms a static transcript page into an interactive meeting review experience. High visual impact, well-understood HTML5 Audio API implementation pattern. Builds on existing `TranscriptView` and `UtteranceBubble` components.

2. **Editable speaker labels + basic speaker stats** -- Makes diarization output usable. "Speaker 1 talked 62% of the time" becomes "Ahmed (PM) talked 62% of the time." Stats already computed backend-side, just need rendering.

3. **Post-recording popup with document upload** -- Entry point for document attachments. Improves the recording flow (name + project + docs) and enables the context injection pipeline.

4. **Document context injection into generation** -- The key differentiator. "Upload your existing spec and Allure generates a PRD that references it" is a compelling FYP demo moment. Simple prompt concatenation, no RAG infrastructure needed.

5. **Product-focused diagram generation + prompt improvements** -- Prompt rewrites that make diagrams model the product discussed, not the meeting itself. Low effort, high quality improvement. Iterative tuning.

Defer to end or stretch:
- **AgglomerativeClustering**: Backend-only improvement, not visible in demo. Do it but don't block features on it.
- **Extended speaker statistics (WPM, pauses)**: Nice-to-have beyond basic talk-time. Quick win if time permits.
- **Meeting-level statistics card**: Low complexity, low demo impact. Fill in at the end.

## Complexity Budget

| Feature Group | Estimated Effort | Risk Level |
|---------------|-----------------|------------|
| Audio playback + transcript sync | 2-3 days | Low -- well-understood HTML5 Audio API pattern, existing component structure supports it |
| Speaker labels + roles + basic stats | 1-2 days | Low -- UI work + simple persistence via speaker mapping object |
| Post-recording popup | 1 day | Low -- modal dialog, state management with existing Zustand store |
| Document attachments (upload + storage + text extraction) | 2 days | Medium -- file upload plumbing + PDF text extraction (need pdfplumber or similar) |
| Context injection into generation | 1 day | Low -- prompt modification, token budget management within 4096 context |
| Product-focused prompt rewrites | 1 day | Medium -- prompt quality is iterative, needs testing with real recordings |
| AgglomerativeClustering swap | 0.5-1 day | Medium -- needs distance_threshold tuning with real audio samples |
| Extended speaker stats | 0.5-1 day | Low -- pure computation from existing utterance timing data |
| Meeting-level stats card | 0.5 day | Low -- render existing data in stat card layout |
| Mermaid syntax validation | 0.5 day | Low -- parse + auto-fix common LLM output issues |

**Total estimated: 10-13 days for full v1.1 scope, 7-9 days for recommended MVP subset.**

## Sources

- [Metaview: Syncing a Transcript with Audio in React](https://www.metaview.ai/resources/blog/syncing-a-transcript-with-audio-in-react)
- [transcript-tracer-js: Sync audio with text using WebVTT timestamps](https://github.com/samuelbradshaw/transcript-tracer-js)
- [Otter vs Fireflies vs Fathom comparison (2025)](https://www.index.dev/blog/otter-vs-fireflies-vs-fathom-ai-meeting-notes-comparison)
- [Fathom vs Fireflies.ai vs Otter.ai (2026)](https://genesysgrowth.com/blog/fathom-vs-fireflies-ai-vs-otter-ai)
- [ECAPA-TDNN Embeddings for Speaker Diarization (arxiv)](https://arxiv.org/abs/2104.01466)
- [SpeechBrain spkrec-ecapa-voxceleb model](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)
- [MermaidSeqBench: LLM-to-Mermaid Benchmark (NeurIPS 2025)](https://arxiv.org/abs/2511.14967)
- [Context Injection Methods for RAG](https://apxml.com/courses/getting-started-rag/chapter-4-rag-generation-augmentation/context-injection-methods)
- [Speaker Diarization Guide 2025](https://www.shadecoder.com/topics/speaker-diarization-a-comprehensive-guide-for-2025)
- [Dashboard UX Design Principles 2025](https://www.uxpin.com/studio/blog/dashboard-design-principles/)

