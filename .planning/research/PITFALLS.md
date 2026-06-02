# Domain Pitfalls

**Domain:** v1.1 features -- audio playback sync, speaker analytics, document attachments, AgglomerativeClustering, product-focused diagram generation -- added to existing meeting transcription app
**Researched:** 2026-03-18
**Scope:** Pitfalls specific to ADDING these features to the existing v1.0 codebase

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Audio Playback Timing Drift from `timeupdate` Event Granularity

**What goes wrong:** The HTML5 `timeupdate` event fires at only 3-5 Hz (roughly every 200-300ms), not per-frame. When using `timeupdate` alone to highlight the active transcript line, users experience a noticeable lag where the highlight jumps to the next line well after the audio has moved past a segment boundary. On longer recordings (10+ minutes), accumulated rounding from the browser's `currentTime` double-precision float can cause the highlight to be off by an entire utterance.

**Why it happens:** Developers assume `timeupdate` is high-frequency and precise. It is neither -- frequency depends on system load and browser implementation (MDN documents 4-66 Hz range). Additionally, the existing transcript segments have `startTime`/`endTime` in seconds from Moonshine Voice, but browser `currentTime` precision varies by browser (Firefox had a documented low-precision bug at `bugzilla.mozilla.org/587465`).

**Consequences:** Transcript highlight feels laggy and disconnected from audio. Click-to-seek puts playhead at wrong position. Users lose trust in the sync feature, which is the centerpiece of v1.1.

**Prevention:**
- Use `requestAnimationFrame` polling loop when audio is playing, NOT `timeupdate` events. Throttle the rAF callback to ~10Hz (check every 100ms) to balance responsiveness with CPU usage. Fall back to `timeupdate` only when tab is backgrounded (rAF pauses in background tabs).
- Round `currentTime` comparisons with a tolerance window (e.g., 150ms) rather than exact equality.
- Use binary search on sorted segments array for O(log n) active-segment lookup instead of linear scan.
- Store segment boundaries as a pre-sorted array once on transcript load, not recomputed per frame.

**Detection:** Test with a 30+ minute recording. If highlight ever lags more than ~200ms behind audible speech changes, the sync mechanism is too slow.

**Phase:** Must be addressed in the audio playback phase. This is architectural -- retrofitting from `timeupdate` to rAF later requires rewriting the entire sync loop.

**Confidence:** HIGH -- well-documented browser behavior, MDN sources confirm.

---

### Pitfall 2: AgglomerativeClustering `distance_threshold` vs `n_clusters` Mutual Exclusion and Cosine Distance Range Confusion

**What goes wrong:** The current system uses MeanShift in `transcription.py` (auto-determines speaker count). Switching to AgglomerativeClustering requires choosing between `n_clusters` (must know speaker count upfront) or `distance_threshold` (auto-determine count from embedding similarity). Teams often set `distance_threshold` without understanding the cosine distance range, leading to either all speakers merged into one cluster or every window becoming its own speaker.

**Why it happens:** sklearn's AgglomerativeClustering has a non-obvious constraint: `n_clusters` and `distance_threshold` are mutually exclusive -- setting both raises an error. When using `metric="cosine"`, distances range from 0 (identical) to 2 (opposite), NOT -1 to 1 as some developers assume. A threshold of 0.5 with cosine may merge too aggressively, while 1.5 may barely cluster at all. There is an open sklearn issue (#27434) documenting confusion around cosine `distance_threshold` behavior. Furthermore, `linkage="ward"` only accepts euclidean -- using it with cosine raises an error.

**Consequences:** Diarization produces wrong speaker count -- either one mega-speaker or dozens of micro-speakers. Since diarization feeds into speaker stats, transcript display, and extraction evidence refs, a bad clustering result cascades through the entire pipeline. Existing tests against MeanShift baselines will not catch this.

**Prevention:**
- Use `distance_threshold` mode (not `n_clusters`) since meeting participant count is unknown.
- Start with `distance_threshold=0.7` for cosine metric on ECAPA-TDNN embeddings -- this is a well-tested starting point for speaker verification tasks.
- Use `linkage="average"` with cosine (NOT `linkage="ward"` which only accepts euclidean).
- Validate by comparing AgglomerativeClustering output against current MeanShift output on 5+ test recordings before swapping. Keep MeanShift as a fallback.
- Add a sanity check: if clustering produces more than 10 speakers or fewer than 2 on multi-speaker audio, log a warning and fall back to MeanShift.

**Detection:** Run both MeanShift and AgglomerativeClustering on the same test recordings. If speaker counts diverge by more than 1, investigate threshold tuning.

**Phase:** Diarization upgrade phase. Must have test recordings with known speaker counts to validate.

**Confidence:** HIGH -- sklearn docs and GitHub issue #27434 confirm the mutual exclusion constraint and cosine range behavior.

---

### Pitfall 3: Document Context Injection Blows Past LLM Context Window

**What goes wrong:** When document attachments (PDFs, DOCX) are parsed and injected as additional context for PRD/Mermaid generation, the combined prompt (system prompt + outcomes + document text) exceeds the 4096-token `n_ctx` configured for Phi-4-mini in `main.py` line 80. The LLM either truncates silently (producing incomplete output), throws an error, or hangs.

**Why it happens:** The current `n_ctx=4096` is already tight for extraction (transcript text + system prompt + JSON schema). Adding document text (a typical PRD or requirements doc is 2000-5000 tokens) will routinely overflow. Critically, `n_ctx` in llama.cpp is the TOTAL window including both input and output -- it is not separate input/output budgets. With `max_tokens=4096` for generation and `n_ctx=4096`, there is effectively zero room for input if max output is ever reached.

**Consequences:** Generation silently produces truncated or garbage output. Users upload a 10-page requirements doc, get back a PRD that references only the first page. Or the backend crashes with an opaque llama.cpp error.

**Prevention:**
- Increase `n_ctx` to at least 8192 (Phi-4-mini supports up to 16384). Measure inference latency impact on M3 before committing to higher values.
- Implement a token budget system: reserve 1500 tokens for system prompt, 1500 for outcomes, cap document context at `n_ctx - 3000 - max_tokens`.
- Summarize long documents before injection -- extract headings, bullet points, and first sentences of paragraphs rather than injecting full text.
- Add a token counting step (use llama.cpp's tokenizer via `llama_cpp.Llama.tokenize()` or a fast approximation like `len(text) // 4`) before building the prompt. If over budget, truncate document context and return a warning to the user.

**Detection:** Test with a 5+ page PDF attached. If generated PRD does not reference content from the last page, context truncation is happening silently.

**Phase:** Document attachment phase. Must be addressed before document context injection is implemented, as it determines the entire prompt architecture.

**Confidence:** HIGH -- confirmed by reading `main.py` line 80 (`n_ctx=4096`) and `document_generation.py` which already uses the full window for outcomes alone.

---

### Pitfall 4: Mermaid Diagrams Model the Meeting Flow, Not the Product

**What goes wrong:** Current prompts in `document_generation.py` ask the LLM to generate diagrams "from meeting outcomes." The LLM produces diagrams showing the meeting discussion flow (e.g., "Team discusses feature A -> Team argues about B -> Decision made on C") rather than the actual product being discussed (e.g., "User logs in -> Selects project -> Uploads recording -> Views transcript"). This is the explicit v1.1 goal: "diagrams model the product discussed, not meeting flow."

**Why it happens:** The existing prompts (lines 7-65 of `document_generation.py`) provide outcomes as input and ask for diagrams. Outcomes are meeting artifacts (decisions, action items, requirements, blockers) -- they describe what was SAID, not what the product DOES. Without explicit instruction to synthesize a product model from the discussion, the LLM defaults to summarizing the input structure.

**Consequences:** Generated diagrams are useless for product documentation. A user flow diagram should show the product's user journey, but instead shows "Speaker 1 proposed X -> Speaker 2 agreed -> Action item assigned." This defeats the entire purpose of the diagram generation feature.

**Prevention:**
- Restructure prompts to have two phases: (1) "From these meeting outcomes and attached documents, identify the product/system being discussed and its core user journeys/entities" (2) "Generate a Mermaid diagram for that product."
- Add explicit negative instructions: "Do NOT diagram the meeting discussion itself. Do NOT include speaker names, meeting actions, or discussion steps. Diagram the product or system the participants are designing/discussing."
- Include document context (attached docs) as PRIMARY product context, with outcomes as supplementary. Attached documents like PRDs or specs describe the product directly; outcomes describe discussion about it.
- Add few-shot examples in the prompt showing the transformation from meeting-about-product to product-diagram.
- Consider a two-pass approach: first LLM call extracts product entities/flows into a structured intermediate, second generates Mermaid from that intermediate.

**Detection:** Generate diagrams from 3 different recordings. If any diagram node contains words like "discussed," "proposed," "agreed," "Speaker," or "meeting," the prompt is still modeling the meeting, not the product.

**Phase:** Diagram generation improvement phase. This is a prompt engineering problem -- can be iterated without code changes, but must be validated before shipping.

**Confidence:** HIGH -- confirmed by reading existing prompts in `document_generation.py`.

---

## Moderate Pitfalls

### Pitfall 5: PDF/DOCX Parsing Fails Silently on Scanned or Complex Documents

**What goes wrong:** Users upload scanned PDFs (image-only, no text layer), password-protected files, or DOCX with embedded charts/tables. The parser returns empty string or garbled text. The system proceeds with empty document context, producing the same output as if no document was attached -- but the user thinks their document was used.

**Why it happens:** PDF structure varies wildly. Multi-column layouts, nested tables, and scanned images all cause extraction tools to return partial or empty results. Standard Python PDF libraries (pypdf, pdfminer) handle text-layer PDFs well but fail silently on image-only PDFs. DOCX embedded objects (charts, SmartArt) are ignored by python-docx.

**Prevention:**
- After parsing, check if extracted text length is below a minimum threshold (e.g., 50 characters for a multi-page doc). If so, return a clear error to the user: "Could not extract text from this document."
- Use `pypdf` for PDF text extraction (lightweight, pure Python, well-maintained). Do NOT add OCR (pytesseract/Tesseract) -- it adds massive dependency complexity for an FYP.
- For DOCX, use `python-docx` which handles paragraphs and tables well but will miss embedded images/charts. Document this limitation.
- Run document parsing in a thread with a 30-second timeout. Malformed PDFs can cause parsing libraries to hang indefinitely.
- Validate file type by magic bytes (first few bytes of file), not just extension. A `.pdf` extension on a non-PDF file should be rejected.
- Accept only PDF, DOCX, and TXT. Reject other formats with clear messaging.

**Detection:** Upload a scanned PDF (screenshot saved as PDF). If the system accepts it silently and produces output identical to no-document-attached, the validation is missing.

**Phase:** Document upload phase. Must implement validation before wiring parsing output into generation prompts.

**Confidence:** HIGH -- well-documented PDF parsing challenges, confirmed by multiple sources.

---

### Pitfall 6: Speaker Statistics Computed from Merged Segments Give Wrong Turns and WPM

**What goes wrong:** The v1.1 spec requires per-speaker statistics: time, words, WPM, turns, avg turn duration, pauses, avg pause duration. The current `calculate_speaker_stats` in `transcription.py` only computes `talk_time_pct` and `utterance_count` from already-merged segments. Computing turns from merged segments gives wrong results because `merge_consecutive_segments` combines consecutive same-speaker segments into one, losing individual turn boundaries.

**Why it happens:** The merge step (`merge_consecutive_segments`, line 257) is designed to reduce visual clutter in the transcript display. But it destroys information needed for turn-level statistics. After merging, a speaker who had 5 quick turns appears to have 1 long turn if all 5 were consecutive.

**Consequences:** Speaker analytics show inflated turn durations and deflated turn counts. WPM calculated from merged segments is correct (total words / total time), but turn-level metrics are wrong. Dashboard stats mislead users about meeting dynamics.

**Prevention:**
- Compute turn-level statistics BEFORE the merge step in the pipeline. Specifically, calculate turns, avg turn duration, and pauses from the pre-merge aligned segments.
- Compute word count per segment from text (split by whitespace) before merging, then aggregate per speaker.
- Store both pre-merge stats and the merged segments in the transcript result. The `run_transcription` pipeline should return stats computed at the right pipeline stage.
- Pause detection: a pause is silence between consecutive segments from the same speaker. Calculate from gaps between consecutive same-speaker segments in the pre-merge data.

**Detection:** Record a meeting where one speaker has many short interjections. If their turn count shows 1-2 turns instead of many, stats are computed post-merge.

**Phase:** Speaker statistics phase. Requires modifying the transcription pipeline -- must be coordinated with the AgglomerativeClustering change to avoid double-refactoring.

**Confidence:** HIGH -- confirmed by reading `transcription.py` lines 257-314 where merge happens before stats return.

---

### Pitfall 7: Click-to-Seek Fails on WebM Audio Files in Safari

**What goes wrong:** The app records audio as WebM (via MediaRecorder API, the default on Chrome). Safari has historically poor support for seeking within WebM containers. When a user clicks a transcript line to seek, Safari either ignores the seek, jumps to 0, or throws a `NotSupportedError`. Even on Chrome, WebM files recorded by MediaRecorder may lack proper Cues (seek index) for random access.

**Why it happens:** The recording pipeline saves as WebM. The backend converts to WAV for processing (`convert_to_wav` in `audio_utils.py`), but the original WebM is what would be played back in the browser. WebM seeking requires the file to have proper Cues metadata which MediaRecorder does not always write correctly for audio-only streams.

**Prevention:**
- Serve the converted WAV file for playback, not the original WebM. WAV has perfect seek support across all browsers. The WAV already exists on the backend (created by `convert_to_wav`).
- Add a backend endpoint to serve the WAV file: `GET /recordings/{job_id}/audio` that returns the WAV with proper `Content-Type: audio/wav` and `Accept-Ranges: bytes` headers.
- If WAV file size is a concern (16kHz mono WAV is ~1.9MB/min, so a 30-min recording is ~57MB), transcode to MP3 or AAC for playback via ffmpeg.
- Test playback and seeking explicitly on Safari, Firefox, and Chrome before shipping.

**Detection:** Open a recording detail page in Safari, click a transcript utterance at the 5-minute mark. If the audio does not seek to that point, WebM seeking is broken.

**Phase:** Audio playback phase. Must decide the playback format before building the sync UI.

**Confidence:** MEDIUM -- based on known WebM/Safari compatibility issues; specific behavior may have improved in recent Safari versions. Needs testing.

---

### Pitfall 8: Dual-Database Architecture Creates Document Attachment Inconsistency

**What goes wrong:** The app has two separate SQLite databases: frontend (`allure-frontend.db` via better-sqlite3 in `src/lib/db/index.ts`) for recordings/tasks/documents, and backend (`allure.db` via Python sqlite3 in `backend/storage.py`) for jobs/transcripts/outcomes. Document attachments need to be associated with recordings (frontend DB) but their parsed text needs to be available to the backend for generation. This split causes inconsistency and forces awkward data passing.

**Why it happens:** The v1.0 architecture intentionally split storage for offline resilience. But document attachments span both worlds: the file metadata and recording association lives in the frontend, while the parsed text content is consumed by the backend's generation endpoints.

**Prevention:**
- Store document attachment files on the filesystem (in the same `uploads/` directory as audio files), referenced by job_id.
- When calling generation endpoints, send the parsed document text as part of the request body. Do NOT try to make the backend read from the frontend DB.
- The frontend handles: file upload UI, storing file metadata, calling a backend endpoint to upload the document.
- The backend handles: receiving the document file, parsing text, storing parsed text alongside the job record, using it during generation.
- Add a `document_context` column to the backend `jobs` table, or a new `job_documents` table.

**Detection:** Upload a document, then generate a PRD. If the backend cannot access the document content, the architecture boundary was not planned for.

**Phase:** Document upload phase. Architecture decision must be made before any document code is written.

**Confidence:** HIGH -- confirmed by reading both `storage.py` (backend DB) and `src/lib/db/index.ts` (frontend DB) showing completely separate databases.

---

### Pitfall 9: Post-Recording Popup Blocks the Processing Pipeline Start

**What goes wrong:** The v1.1 spec includes a "post-recording popup (name, project, doc upload) with background processing." If the popup must be completed before audio is uploaded to the backend, there is a delay between recording end and processing start. Users who dismiss the popup or navigate away lose their recording or delay processing indefinitely.

**Why it happens:** The current flow in `use-audio-recorder.ts` and the recordings API is: record -> stop -> upload to backend -> processing starts. Adding a popup between stop and upload creates a window where audio sits in the browser with no backend job.

**Prevention:**
- Upload audio to backend IMMEDIATELY when recording stops, before showing the popup. Get the `job_id` back. Processing starts in the background.
- The popup then updates metadata (name, project assignment, document attachments) on the already-created job via PATCH requests.
- This means the backend needs a metadata update endpoint (currently missing -- there is no PATCH on `/recordings/{job_id}`). Add `PATCH /recordings/{job_id}` for name/project updates.
- Document attachments can be uploaded asynchronously while STT is running. They are only needed at generation time, not transcription time.

**Detection:** Record audio, then intentionally close the popup without completing it. If the recording is lost or processing never starts, the upload is gated on popup completion.

**Phase:** Post-recording popup phase. This is a UX flow decision with backend API implications.

**Confidence:** HIGH -- confirmed by reading the current upload flow in `main.py` and the absence of a PATCH endpoint.

---

## Minor Pitfalls

### Pitfall 10: Editable Speaker Labels Not Persisted Backend-Side

**What goes wrong:** Users rename "Speaker 1" to "Alice" in the transcript tab. The rename is stored frontend-side only. When regenerating a PRD or diagram, the backend still sees "Speaker 1" in the transcript segments because it reads from its own `jobs.result` JSON blob.

**Prevention:** Either (a) add a speaker label mapping to the backend job record and PATCH it when the frontend updates a label, or (b) send current speaker labels as part of generation requests so the backend can substitute them into prompts.

**Phase:** Speaker management phase.

**Confidence:** HIGH -- confirmed by separate DB architecture.

---

### Pitfall 11: Mermaid Syntax Errors from Phi-4-mini Not Handled Gracefully

**What goes wrong:** Smaller LLMs frequently generate invalid Mermaid syntax -- unclosed brackets, special characters in labels (parentheses, colons, quotes), or incorrect relationship syntax in ERDs. The current `MermaidDiagram` component in `src/components/document/mermaid-diagram.tsx` likely renders nothing or shows a cryptic error.

**Prevention:**
- Strip common LLM artifacts before rendering: markdown code fences (` ```mermaid ... ``` `), explanation text before/after the code, stray quotes.
- Implement a validation-and-retry loop on the backend: render attempt with mermaid CLI or regex validation, if invalid, send code + error back to LLM asking for a fix. Limit to 2 retries.
- Add a raw-code fallback view in the UI so users can see and manually fix the Mermaid source.
- In the prompt, add explicit rules about characters that break Mermaid: no parentheses in node labels, no colons except in relationship syntax.

**Phase:** Diagram generation phase.

**Confidence:** MEDIUM -- common LLM behavior; Phi-4-mini's specific Mermaid generation quality needs testing.

---

### Pitfall 12: requestAnimationFrame Sync Loop Drains Battery on Long Recordings

**What goes wrong:** Running rAF at 60fps continuously while audio plays consumes CPU unnecessarily for transcript sync (which only needs ~10Hz updates). On laptops, this noticeably impacts battery life for hour-long recordings.

**Prevention:** Throttle the rAF callback to check active segment only every 100ms (10Hz) using a timestamp delta check inside the rAF loop. Cancel the rAF loop when audio is paused or the component unmounts. This gives sub-200ms sync accuracy while reducing CPU usage by ~90%.

**Phase:** Audio playback phase.

**Confidence:** HIGH -- standard web performance concern.

---

### Pitfall 13: Meeting-Level Statistics Double-Count Overlapping Diarization Windows

**What goes wrong:** The current `FastDiarizer` uses overlapping windows (10s window, 2s hop). When computing meeting-level duration statistics from diarization segments, naive summation of segment durations overcounts because windows overlap. A 60-second recording with 10s/2s windows produces segments that sum to much more than 60 seconds.

**Prevention:** Use the audio file's actual duration (from `librosa.get_duration`) for meeting duration, not the sum of diarization segment durations. For speaker talk time, use the MERGED segment durations (after overlap resolution), not raw window durations.

**Phase:** Meeting statistics phase.

**Confidence:** HIGH -- confirmed by reading `FastDiarizer.diarize()` in `transcription.py` which uses overlapping windows.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Audio playback sync | `timeupdate` too slow for responsive highlighting | Use rAF polling loop throttled to ~10Hz |
| Audio playback sync | WebM seek broken in Safari | Serve WAV or transcoded audio for playback |
| Audio playback sync | rAF loop drains battery | Throttle to 100ms intervals, cancel on pause |
| Speaker statistics | Stats computed from wrong pipeline stage (post-merge) | Compute turn-level stats before merge step |
| Speaker statistics | Overlapping diarization windows inflate duration sums | Use actual audio duration from librosa |
| Speaker label editing | Label changes not visible to backend | PATCH labels to backend or send with generation requests |
| Document upload | Scanned/complex PDFs return empty text silently | Validate extracted text length, reject with clear error |
| Document context injection | Combined prompt overflows 4096 context window | Increase n_ctx to 8192+, implement token budget |
| Document architecture | Dual-DB split complicates document flow | Frontend uploads to backend, backend owns parsed text |
| Post-recording popup | Popup gates upload, risking data loss | Upload immediately, popup updates metadata after |
| AgglomerativeClustering | Wrong distance_threshold with cosine metric | Start at 0.7, use average linkage, validate against MeanShift |
| AgglomerativeClustering | n_clusters and distance_threshold mutually exclusive | Use distance_threshold mode for unknown speaker counts |
| Diagram generation | LLM diagrams model the meeting, not the product | Two-phase prompt: extract product model, then diagram it |
| Diagram generation | Mermaid syntax errors from LLM | Validate + retry loop, strip code fences, raw-code fallback |

## Sources

- [MDN: HTMLMediaElement timeupdate event](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/timeupdate_event)
- [MDN: HTMLMediaElement currentTime property](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/currentTime)
- [Firefox bug 587465: audio.currentTime has low precision](https://bugzilla.mozilla.org/show_bug.cgi?id=587465)
- [sklearn AgglomerativeClustering documentation](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.AgglomerativeClustering.html)
- [sklearn issue #27434: distance_threshold behavior with cosine metric](https://github.com/scikit-learn/scikit-learn/issues/27434)
- [Speaker Diarization: A Comprehensive Guide for 2025](https://www.shadecoder.com/topics/speaker-diarization-a-comprehensive-guide-for-2025)
- [Simple Speaker Diarization with SpeechBrain X-Vectors](https://huggingface.co/blog/norwooodsystems/simple-speaker-diarization-speechbrain)
- [Challenges Parsing PDFs with Python](https://www.theseattledataguy.com/challenges-you-will-face-when-parsing-pdfs-with-python-how-to-parse-pdfs-with-python/)
- [Best Python PDF to Text Parser Libraries: A 2026 Evaluation](https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/)
- [GenAIScript: Mermaids Unbroken -- fixing LLM Mermaid syntax](https://microsoft.github.io/genaiscript/blog/mermaids/)
- [AI Mermaid Diagram Generator That Fixes Its Own Mistakes](https://djajafer.medium.com/i-built-an-ai-mermaid-diagram-generator-that-fixes-its-own-mistakes-26552047c37a)
- [Speaker Diarization textbook -- Aalto University](https://speechprocessingbook.aalto.fi/Recognition/Speaker_Diarization.html)
- Codebase analysis: `backend/main.py`, `backend/transcription.py`, `backend/document_generation.py`, `backend/extraction.py`, `backend/storage.py`, `src/lib/db/index.ts`, `src/lib/db/recordings.ts`

