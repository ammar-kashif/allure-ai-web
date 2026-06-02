# Technology Stack

**Project:** Allure AI v1.1 -- Meeting Intelligence & Document Context
**Researched:** 2026-03-18
**Scope:** NEW additions/changes only. Existing stack (Next.js 15, FastAPI, SQLite, TanStack Query, shadcn/ui, Zustand, Moonshine Voice, SpeechBrain, scikit-learn, llama-cpp-python, Mermaid) is validated and unchanged.

## New Dependencies for v1.1

### Backend (Python)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyMuPDF | >=1.27 | PDF text extraction | Fastest Python PDF extractor (3-5x faster than pypdf/pdfplumber). No mandatory external C dependencies beyond what ships with the wheel. Handles complex layouts, preserves reading order. Current version 1.27.2 (Feb 2026). | HIGH |
| python-docx | >=1.1 | Word document (.docx) text extraction | Standard library for .docx parsing. Lightweight, deterministic paragraph/table extraction. Current version 1.2.0 (Jun 2025). Python >=3.9. | HIGH |

### Frontend (Node)

**No new npm packages needed for v1.1.**

Audio playback uses native browser APIs. Speaker statistics rendering uses existing shadcn/ui. Document upload uses standard file inputs. All new UI is built with the existing component library.

## Feature-by-Feature Stack Decisions

### 1. Audio Playback Synced with Transcript

**Approach:** Native HTML5 `<audio>` element + React refs + Zustand playback store.

**Why no library:**
The browser `<audio>` element provides everything needed: `currentTime` (read/write for seeking), `play()`/`pause()`, `timeupdate` event (~4Hz for highlight tracking), `duration`, `seeking`/`seeked` events. The transcript segments already have `start`/`end` timestamps from the backend. This is a straightforward mapping -- no waveform visualization or advanced audio processing is needed.

**Implementation pattern:**
- `useRef<HTMLAudioElement>` holds the player instance.
- `timeupdate` listener compares `currentTime` against segment boundaries to determine active line.
- Click handler on transcript segments: `audioRef.current.currentTime = segment.start`.
- Zustand slice stores `{ isPlaying, currentTime, activeSegmentIndex }` so components outside the player (mini-bar, transcript panel) can react.
- Audio source: new `GET /recordings/{job_id}/audio` endpoint serving the file via FastAPI's `FileResponse` (supports Range requests for browser seeking).

**What NOT to add:**
| Library | Why Not |
|---------|---------|
| wavesurfer.js | 200KB+ for waveform visualization we do not need. Allure's UX is transcript-centric, not waveform-centric. If waveform is desired later, it can be added independently. |
| howler.js | Web Audio API wrapper for games/spatial audio. Adds complexity for no benefit over `<audio>`. |
| transcript-tracer-js | Designed for WebVTT-based sync. Our data is already JSON segments with timestamps -- converting to VTT adds an unnecessary serialization step. |
| react-player | Wrapper for video/audio embeds (YouTube, etc). We serve our own files; native `<audio>` is simpler. |

### 2. Speaker Statistics Computation

**Approach:** Expand existing `calculate_speaker_stats()` in `transcription.py`. No new libraries.

The current function already computes `talk_time_pct` and `utterance_count`. v1.1 adds:

| Statistic | Computation | Library Needed |
|-----------|-------------|----------------|
| `talk_time_seconds` | Sum of `(end - start)` per speaker | None (Python math) |
| `word_count` | `sum(len(seg["text"].split()) for seg in speaker_segments)` | None |
| `wpm` | `word_count / (talk_time_seconds / 60)` | None |
| `avg_turn_seconds` | `talk_time_seconds / utterance_count` | None |
| `pause_count` | Count gaps > 2s between consecutive same-speaker segments | None |
| `avg_pause_seconds` | Mean of those gaps | None |

All derived from existing segment data (`start`, `end`, `text`, `speaker`). Pure Python arithmetic.

**Meeting-level statistics** (duration, processing time, speaker count, attached doc count) are similarly trivial aggregations from existing data.

### 3. Document Upload & Text Extraction

**Approach:** PyMuPDF for PDF, python-docx for DOCX, built-in `open()` for TXT/MD.

**Supported formats:** `.pdf`, `.docx`, `.txt`, `.md`

| Format | Library | Extraction Pattern |
|--------|---------|-------------------|
| PDF | PyMuPDF | `fitz.open(path)` then `page.get_text()` per page |
| DOCX | python-docx | `Document(path)` then iterate `doc.paragraphs` |
| TXT | built-in | `open(path).read()` |
| MD | built-in | `open(path).read()` (treat as plain text for LLM context) |

**Backend integration:**
1. New endpoint: `POST /recordings/{job_id}/documents` -- accepts multipart file upload.
2. New endpoint: `GET /recordings/{job_id}/documents` -- list attached documents.
3. New SQLite table:
   ```sql
   CREATE TABLE documents (
       id TEXT PRIMARY KEY,
       job_id TEXT NOT NULL REFERENCES jobs(id),
       filename TEXT NOT NULL,
       content_text TEXT NOT NULL,
       created_at TEXT NOT NULL DEFAULT (datetime('now'))
   );
   ```
4. Document text is injected into PRD/diagram prompts as additional context (see section 5).

**What NOT to add:**
| Library | Why Not |
|---------|---------|
| unstructured | Massive dependency tree (pulls in ML models, detectron2, etc). Overkill for extracting text from standard digital documents. |
| langchain document loaders | Unnecessary abstraction layer. Direct `fitz.open()` / `Document()` calls are 5 lines of code. |
| pdfplumber | Slower than PyMuPDF. Better at table extraction, but we need prose text, not structured tables. |
| pypdf | Lighter than PyMuPDF but 3-5x slower and worse at complex layouts. |
| pytesseract / OCR | Scanned documents are out of scope for FYP. Meeting-adjacent docs (specs, PRDs, design docs) are digital-native. |
| mammoth | Converts DOCX to HTML. We need plain text for LLM context, not HTML. |

### 4. AgglomerativeClustering for Diarization

**Approach:** Replace `MeanShift()` with `AgglomerativeClustering()` in `FastDiarizer.diarize()`. Zero new dependencies -- scikit-learn >=1.5 is already installed.

**Why switch from MeanShift:**
- MeanShift uses kernel density estimation, which struggles with high-dimensional speaker embeddings (ECAPA-TDNN produces 192-dim vectors). Bandwidth estimation becomes unreliable.
- AgglomerativeClustering with cosine distance + average linkage is the standard approach in speaker diarization literature. SpeechBrain's own diarization examples use it.
- `distance_threshold` parameter auto-determines speaker count (like MeanShift) but with more stable, reproducible boundaries.

**Implementation:**
```python
from sklearn.cluster import AgglomerativeClustering

# In FastDiarizer.diarize(), replace:
#   clustering = MeanShift()
#   labels = clustering.fit_predict(embedding_matrix)
# With:
clustering = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=1.0,   # tune empirically on test recordings
    metric="cosine",
    linkage="average",
)
labels = clustering.fit_predict(embedding_matrix)
```

**Key tuning parameter:** `distance_threshold`
- Controls when clusters stop merging. Lower = more speakers detected, higher = fewer.
- Start at 1.0 for cosine distance. Test with 2-speaker and 3-speaker recordings to calibrate.
- Can be exposed as an optional API parameter later if needed.

**What stays the same:**
- SpeechBrain ECAPA-TDNN for embedding extraction (works well, already loaded).
- Fixed-window approach for segment extraction (simple, effective for meeting audio).
- Median filter smoothing post-clustering (still valuable).
- Label remapping, boundary snapping, segment merging (all downstream of clustering).

### 5. Product-Focused Diagram Generation (Prompt Engineering)

**Approach:** Rewrite prompts in `document_generation.py`. No new libraries.

**Current problem:** Prompts say "generate from meeting outcomes" which biases the LLM toward modeling the meeting process itself ("Record -> Transcribe -> Review") instead of the product discussed in the meeting.

**Changes needed:**
1. **Rewrite system prompts** to explicitly instruct: "Model the PRODUCT or SYSTEM discussed in this meeting, NOT the meeting process."
2. **Add negative examples:** "Do NOT include nodes like 'Meeting', 'Recording', 'Transcription', 'Review Outcomes'."
3. **Inject document context** from attached documents:
   ```python
   doc_context = ""
   if attached_documents:
       doc_context = "\n\n## Reference Documents\n"
       for doc in attached_documents:
           # Truncate to ~2000 chars per doc to stay within 4096 context window
           doc_context += f"\n### {doc['filename']}\n{doc['content_text'][:2000]}\n"
   ```
4. **Product context extraction:** Optionally add a pre-step that asks the LLM "What product/system is being discussed?" and feeds that answer into the diagram prompt.

**Context window constraint:** Phi-4-mini runs with `n_ctx=4096`. With outcomes (~500-1000 tokens), system prompt (~300 tokens), and generation headroom (~2000 tokens), there is roughly ~800-1200 tokens available for document context. Truncation to ~2000 chars per document (approximately 500 tokens) is necessary. If multiple documents are attached, limit to the 2 most relevant or let the user select which to include.

### 6. Audio Serving Endpoint

**Approach:** `FastAPI FileResponse` for static file serving. Already part of FastAPI, no new dependency.

**Implementation:**
```python
from fastapi.responses import FileResponse

@app.get("/recordings/{job_id}/audio")
async def get_recording_audio(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return FileResponse(
        job["file_path"],
        media_type="audio/wav",
        filename=job.get("original_filename", f"{job_id}.wav"),
    )
```

`FileResponse` handles `Content-Range` headers needed for browser audio seeking (scrubbing without downloading the entire file).

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Audio playback | Native `<audio>` | wavesurfer.js | 200KB+ for waveform we don't need; transcript-centric UX |
| Audio playback | Native `<audio>` | howler.js | Games/spatial audio wrapper; `<audio>` is simpler |
| PDF extraction | PyMuPDF (>=1.27) | pypdf | 3-5x slower, worse complex layout handling |
| PDF extraction | PyMuPDF (>=1.27) | pdfplumber | Slower; optimized for tables, we need prose |
| PDF extraction | PyMuPDF (>=1.27) | unstructured | Massive dependency tree with ML models |
| DOCX extraction | python-docx (>=1.1) | mammoth | Converts to HTML; we need plain text |
| Clustering | AgglomerativeClustering | Keep MeanShift | Unreliable bandwidth on 192-dim embeddings |
| Clustering | AgglomerativeClustering | SpectralClustering | Requires precomputed affinity matrix; lacks distance_threshold |
| Clustering | AgglomerativeClustering | HDBSCAN | Density-based like MeanShift; same weakness on high-dim; extra dependency |
| Diagram quality | Prompt engineering | Fine-tuned model | Out of scope for FYP |

## Installation

```bash
# Backend -- new dependencies only (run in backend/ directory)
pip install "pymupdf>=1.27" "python-docx>=1.1"
```

Add to `backend/requirements.txt`:
```
pymupdf>=1.27
python-docx>=1.1
```

**Frontend:** No new npm packages. Zero changes to `package.json`.

## Summary

| Feature | Change Type | New Dependencies | Effort |
|---------|-------------|-----------------|--------|
| Audio playback sync | Frontend (React + HTML5 `<audio>`) + backend endpoint | None | Medium |
| Speaker statistics | Backend computation expansion | None | Low |
| Document upload/parsing | Backend endpoints + text extraction | `pymupdf`, `python-docx` | Medium |
| AgglomerativeClustering | Backend swap (MeanShift -> AgglomerativeClustering) | None (already in scikit-learn) | Low |
| Product-focused diagrams | Prompt rewriting in `document_generation.py` | None | Medium (iterative) |
| Audio serving | Backend endpoint (FileResponse) | None (already in FastAPI) | Low |

**Total new dependencies: 2** Python packages (`pymupdf`, `python-docx`). Everything else leverages what is already installed.

## Sources

- [PyMuPDF PyPI -- v1.27.2](https://pypi.org/project/PyMuPDF/) -- latest version, installation
- [python-docx PyPI -- v1.2.0](https://pypi.org/project/python-docx/) -- latest version, Python support
- [scikit-learn AgglomerativeClustering docs](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.AgglomerativeClustering.html) -- distance_threshold API, cosine metric
- [SpeechBrain diarization processing](https://speechbrain.readthedocs.io/en/v1.0.2/API/speechbrain.processing.diarization.html) -- embedding-based diarization patterns
- [Simple Speaker Diarization with SpeechBrain](https://huggingface.co/blog/norwooodsystems/simple-speaker-diarization-speechbrain) -- AgglomerativeClustering with speaker embeddings
- [Metaview: Syncing a Transcript with Audio in React](https://www.metaview.ai/resources/blog/syncing-a-transcript-with-audio-in-react) -- React transcript sync patterns
- [2025 Python PDF Extractor Comparison](https://dev.to/onlyoneaman/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-akm) -- PyMuPDF performance benchmarks
- [2026 Python PDF Library Evaluation](https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/) -- current landscape
- [Codepunker: Sync Audio with Text](https://www.codepunker.com/blog/sync-audio-with-text-using-javascript) -- HTML5 audio timeupdate patterns

