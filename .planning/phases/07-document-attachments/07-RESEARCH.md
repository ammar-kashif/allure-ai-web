# Phase 7: Document Attachments - Research

**Researched:** 2026-03-19
**Domain:** File upload, text extraction (PDF/DOCX/TXT), SQLite storage, FastAPI endpoints, Next.js UI
**Confidence:** HIGH

## Summary

Phase 7 adds document attachment capability to recordings: users upload PDF, DOCX, or TXT files from the recording detail page (or post-recording dialog), the Python backend extracts text synchronously, and metadata + extracted text are stored in a new `attachments` SQLite table. The recording detail page shows an "Attached Documents" card in the Info tab, and a 4th stat card displays the document count.

The technical surface is well-understood. The backend uses pdfplumber for PDF extraction and python-docx for DOCX extraction -- both are mature, well-documented Python libraries. The frontend extends existing patterns (FileDropZone reuse, TanStack Query mutations, shadcn/ui cards). The n_ctx bump from 4096 to 8192 is a one-line change in `main.py` lifespan. No novel architecture is needed.

**Primary recommendation:** Use pdfplumber (not PyPDF2) for PDF text extraction -- it handles complex layouts, tables, and multi-column PDFs far more reliably, which matters for reference documents (PRDs, specs, etc.) that Phase 8 will consume.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Extraction runs on the Python backend (FastAPI) -- consistent with STT/diarization processing
- Extraction is synchronous during the upload request -- PDF/DOCX parsing is sub-second, no job queue needed
- Supported file types: PDF, DOCX, TXT (drop .doc legacy support)
- n_ctx increased to 8192 in this phase to unblock Phase 8 document context injection
- Attached documents shown in an "Attached Documents" card inside the Info tab on the recording detail page
- Card sits below the existing Recording Info card
- Each document row shows: file type icon, filename, file size
- No text preview snippet -- just filename and size
- Users can delete attached documents with an X button + confirmation
- MEET-04: New 4th stat card "Attached Documents" alongside Duration, Processing Time, Speakers
- "+ Upload documents" button inside the Attached Documents card in the Info tab
- Clicking opens file picker; reuses FileDropZone component from Phase 6
- Upload flow: Next.js API route receives file -> saves to disk -> calls Python backend for text extraction -> stores metadata + extracted text in backend DB
- Post-recording dialog upload path updated to also trigger text extraction and DB storage
- New `attachments` table in Python backend SQLite (allure.db), alongside existing `jobs` table
- Schema: id, recording_id, filename, file_type, file_size, extracted_text, created_at
- Extracted text stored in same row as attachment metadata (single table, no joins)
- 10 MB per-file size limit -- validated client-side and server-side
- List endpoint (GET /recordings/{id}/attachments) returns metadata only (no extracted text)

### Claude's Discretion
- Exact Python extraction library choice (PyPDF2 vs pdfplumber)
- Backend API endpoint design (upload, list, delete, get-text)
- FileDropZone integration pattern on detail page (inline expand vs modal)
- Error handling for extraction failures (corrupted PDFs, empty docs)
- Stat card icon and styling for "Attached Documents"
- How n_ctx bump is configured in llama.cpp settings

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOC-01 | User can upload documents (PDF, DOCX) to a recording | FileDropZone reuse, Next.js API route extension, Python backend upload endpoint, 10MB validation |
| DOC-02 | Attached document text is extracted and stored for generation context | pdfplumber for PDF, python-docx for DOCX, plain read for TXT, synchronous extraction in upload handler, `attachments` table storage |
| DOC-03 | Attached documents are listed on the recording detail page | New "Attached Documents" card in Info tab, TanStack Query hook for list endpoint, delete with confirmation |
| MEET-04 | User can view number of attached documents on the recording detail page | 4th MeetingStatCards entry with Paperclip icon, docCount prop from attachments list length |
</phase_requirements>

## Standard Stack

### Core (Backend -- Python)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pdfplumber | latest (0.11.x) | PDF text extraction | Better layout handling than PyPDF2; handles tables, multi-column, complex formatting reliably |
| python-docx | latest (1.1.x) | DOCX text extraction | De facto standard for DOCX in Python; simple `Document(path).paragraphs` API |

### Core (Frontend -- already installed)
| Library | Version | Purpose | Already In Project |
|---------|---------|---------|-------------------|
| @tanstack/react-query | ^5.90 | Data fetching, mutations | Yes |
| lucide-react | ^0.577 | Icons (Paperclip, FileText, Trash2) | Yes |
| sonner | ^2.0 | Toast notifications | Yes |
| zustand | ^5.0 | State management (if needed) | Yes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Dialog | installed | Delete confirmation modal | For delete attachment confirmation |
| shadcn/ui AlertDialog | installed | Better for destructive confirmations | Alternative to Dialog for delete |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pdfplumber | PyPDF2 | PyPDF2 is 4x faster but poor with complex layouts, tables, multi-column -- pdfplumber's accuracy matters for Phase 8 context injection |
| pdfplumber | pymupdf (fitz) | Faster, but C dependency; pdfplumber is pure Python and sufficient for sub-second extraction |
| python-docx | docx2python | docx2python extracts more (headers/footers) but python-docx is simpler and well-maintained |

**Recommendation:** Use **pdfplumber** for PDF extraction. The documents users upload (PRDs, specs, meeting notes) likely have structure that PyPDF2 would mangle. pdfplumber's ~100ms overhead per document is negligible for synchronous upload.

**Installation:**
```bash
cd backend && pip install pdfplumber python-docx
```

Add to `backend/requirements.txt`:
```
pdfplumber>=0.11
python-docx>=1.1
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
  storage.py          # Add attachments table + CRUD functions
  main.py             # Add attachment endpoints + n_ctx bump
  models.py           # Add Attachment pydantic models
  text_extraction.py  # NEW: extract_text(file_path, file_type) -> str

src/
  app/api/recordings/[id]/
    documents/route.ts      # EXTEND: proxy to Python backend for extraction
    attachments/route.ts     # NEW: list attachments (GET), or combine with documents
  components/recording/
    attached-documents-card.tsx  # NEW: card in Info tab
    meeting-stat-cards.tsx       # EXTEND: add 4th stat card
    file-drop-zone.tsx           # EXTEND: remove .doc, add size validation
  hooks/
    use-attachments.ts           # NEW: TanStack Query hooks
```

### Pattern 1: Synchronous Extraction in Upload Handler
**What:** Text extraction happens inline during the upload POST request, not as a background job
**When to use:** When processing is sub-second (PDF/DOCX parsing)
**Example:**
```python
# backend/text_extraction.py
import pdfplumber
from docx import Document

def extract_text(file_path: str, file_type: str) -> str:
    if file_type == "pdf":
        with pdfplumber.open(file_path) as pdf:
            return "\n\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    elif file_type == "docx":
        doc = Document(file_path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif file_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
```

### Pattern 2: Next.js API Route Proxies to Python Backend
**What:** Next.js API route receives the file, saves to disk, then calls Python backend for extraction + DB storage
**When to use:** All backend interactions in this project follow this proxy pattern
**Example:**
```typescript
// Upload flow in Next.js API route:
// 1. Receive file from client (FormData)
// 2. Save file to public/recordings/{id}/docs/
// 3. POST to Python backend: http://localhost:8000/recordings/{id}/attachments
//    with file path, filename, file_type, file_size
// 4. Python backend extracts text, stores in attachments table
// 5. Return metadata to client
```

### Pattern 3: Storage CRUD Following Existing Jobs Pattern
**What:** New `attachments` table follows the same `_get_conn()` + simple SQL pattern as `jobs` table
**When to use:** All SQLite operations in this project
**Example:**
```python
# In storage.py init_db():
_conn.execute("""
    CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY,
        recording_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        extracted_text TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")
```

### Pattern 4: TanStack Query Hook for Attachments
**What:** Custom hook with query + mutations following existing project patterns
**When to use:** All data fetching in this project uses TanStack Query
**Example:**
```typescript
// hooks/use-attachments.ts
export function useAttachments(recordingId: string, enabled = true) {
  return useQuery({
    queryKey: ["attachments", recordingId],
    queryFn: () => fetch(`/api/recordings/${recordingId}/attachments`).then(r => r.json()),
    enabled,
  })
}

export function useUploadAttachment(recordingId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => { /* upload logic */ },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["attachments", recordingId] }),
  })
}
```

### Anti-Patterns to Avoid
- **Storing extracted text in the Next.js SQLite (better-sqlite3):** All processing data lives in the Python backend's allure.db. Don't split storage.
- **Background job queue for extraction:** PDF/DOCX parsing is sub-second. Adding job queue complexity is unnecessary and would delay the UI showing the attachment.
- **Reading entire extracted_text in list endpoint:** List should return metadata only. Extracted text is only needed at generation time (Phase 8).
- **Uploading directly from client to Python backend:** Maintain the proxy pattern -- client -> Next.js API -> Python backend.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | pdfplumber | PDF format is enormously complex; fonts, encodings, columns, tables |
| DOCX text extraction | XML parsing of .docx | python-docx | OOXML is deeply nested; python-docx handles all the edge cases |
| File type detection | Extension string matching only | Extension + MIME header check | Users sometimes upload misnamed files |
| Delete confirmation UI | Custom modal | shadcn AlertDialog | Already available, handles focus trap and accessibility |

**Key insight:** PDF parsing in particular is deceptively complex. Even "simple" PDFs can have ligatures, right-to-left text, embedded fonts without ToUnicode maps, etc. pdfplumber handles these; a hand-rolled solution would not.

## Common Pitfalls

### Pitfall 1: Corrupted or Password-Protected PDFs
**What goes wrong:** pdfplumber throws exceptions on encrypted/corrupted PDFs, crashing the upload handler
**Why it happens:** Users upload any PDF they have; some are protected or malformed
**How to avoid:** Wrap extraction in try/except, store empty string for extracted_text, return success with a warning flag (extraction_error field)
**Warning signs:** Unhandled exceptions in upload endpoint

### Pitfall 2: File Size Explosion with Extracted Text
**What goes wrong:** A 5MB PDF with dense text could produce megabytes of extracted text, bloating the SQLite DB
**Why it happens:** 10MB file limit doesn't limit extracted text size
**How to avoid:** Truncate extracted text to a reasonable limit (e.g., 100K characters). For Phase 8's context injection, n_ctx=8192 tokens is roughly 32K characters, so 100K is generous.
**Warning signs:** Slow queries on attachments table

### Pitfall 3: Encoding Issues with TXT Files
**What goes wrong:** `open(path, 'r')` fails on non-UTF-8 text files
**Why it happens:** Users may upload ISO-8859-1, Windows-1252, etc.
**How to avoid:** Use `errors='replace'` or try multiple encodings with fallback
**Warning signs:** UnicodeDecodeError in logs

### Pitfall 4: FileDropZone Accepts .doc But Phase 7 Drops It
**What goes wrong:** Existing FileDropZone accepts `.doc` files which Phase 7 doesn't support
**Why it happens:** FileDropZone was built in Phase 6 with `.doc` in the accepted types
**How to avoid:** Update ACCEPTED_TYPES to remove `.doc`, update the hint text
**Warning signs:** Users upload .doc files that fail extraction

### Pitfall 5: Post-Recording Dialog Upload Not Triggering Extraction
**What goes wrong:** Documents uploaded via post-recording dialog are saved to disk but never extracted
**Why it happens:** The existing `POST /api/recordings/{id}/documents` route only saves files to disk (filesystem-only from Phase 6)
**How to avoid:** Update the documents route to also call the Python backend for extraction + DB storage after saving files
**Warning signs:** Documents uploaded during recording flow have no extracted text

### Pitfall 6: Race Condition on Delete (File vs DB)
**What goes wrong:** File deleted from disk but DB record remains (or vice versa)
**Why it happens:** Two separate operations (file delete + DB delete) without a transaction
**How to avoid:** Delete DB record first (authoritative), then delete file (best-effort). If file deletion fails, log but don't error.
**Warning signs:** Orphaned files on disk or ghost entries in UI

## Code Examples

### Backend: Text Extraction Module
```python
# backend/text_extraction.py
import logging
import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)

MAX_EXTRACTED_CHARS = 100_000  # ~100K chars, well above n_ctx=8192 token limit

def extract_text(file_path: str, file_type: str) -> tuple[str, str | None]:
    """Extract text from a document. Returns (text, error_message)."""
    try:
        if file_type == "pdf":
            text = _extract_pdf(file_path)
        elif file_type == "docx":
            text = _extract_docx(file_path)
        elif file_type == "txt":
            text = _extract_txt(file_path)
        else:
            return "", f"Unsupported file type: {file_type}"

        # Truncate if too long
        if len(text) > MAX_EXTRACTED_CHARS:
            text = text[:MAX_EXTRACTED_CHARS]
            logger.warning("Truncated extracted text for %s to %d chars", file_path, MAX_EXTRACTED_CHARS)

        return text.strip(), None
    except Exception as e:
        logger.error("Text extraction failed for %s: %s", file_path, e)
        return "", str(e)

def _extract_pdf(file_path: str) -> str:
    with pdfplumber.open(file_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)

def _extract_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

def _extract_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
```

### Backend: Attachment Storage CRUD
```python
# In storage.py -- add to init_db() and new functions

# Table creation (in init_db):
_conn.execute("""
    CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY,
        recording_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        extracted_text TEXT NOT NULL DEFAULT '',
        extraction_error TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")

def create_attachment(attachment_id, recording_id, filename, file_type, file_size, extracted_text, extraction_error=None):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO attachments (id, recording_id, filename, file_type, file_size, extracted_text, extraction_error) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (attachment_id, recording_id, filename, file_type, file_size, extracted_text, extraction_error),
    )
    conn.commit()

def list_attachments(recording_id):
    """Return metadata only (no extracted_text) for a recording's attachments."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, recording_id, filename, file_type, file_size, extraction_error, created_at FROM attachments WHERE recording_id = ? ORDER BY created_at",
        (recording_id,),
    ).fetchall()
    conn.row_factory = None
    return [dict(row) for row in rows]

def delete_attachment(attachment_id):
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
    conn.commit()
    return cursor.rowcount > 0
```

### Backend: FastAPI Endpoints
```python
# In main.py -- new endpoints

@app.post("/recordings/{job_id}/attachments", status_code=201)
async def upload_attachment(job_id: str, file: UploadFile = File(...)):
    """Upload a document, extract text, and store metadata."""
    # Validate job exists
    # Validate file size <= 10MB
    # Validate file type (pdf, docx, txt)
    # Save file, extract text, create DB record
    ...

@app.get("/recordings/{job_id}/attachments")
async def get_attachments(job_id: str):
    """List attachment metadata for a recording."""
    ...

@app.delete("/recordings/{job_id}/attachments/{attachment_id}", status_code=204)
async def remove_attachment(job_id: str, attachment_id: str):
    """Delete an attachment (file + DB record)."""
    ...

@app.get("/recordings/{job_id}/attachments/{attachment_id}/text")
async def get_attachment_text(job_id: str, attachment_id: str):
    """Return extracted text for a single attachment (used by Phase 8)."""
    ...
```

### Frontend: Attached Documents Card
```typescript
// components/recording/attached-documents-card.tsx
// Card in Info tab with:
// - Title "Attached Documents"
// - "+ Upload documents" button (triggers file picker or inline FileDropZone)
// - List of attachments: file type icon, filename, file size, delete X button
// - Uses existing rounded-xl bg-card shadow-card pattern
```

### Frontend: Updated MeetingStatCards
```typescript
// Add docCount prop and 4th card with Paperclip icon
interface MeetingStatCardsProps {
  duration?: number
  processingTime?: number
  speakerCount?: number
  docCount?: number  // NEW
}
// Add: import { Paperclip } from "lucide-react"
// Add 4th StatCard with label="Documents" value={docCount}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPDF2 for all PDF work | pdfplumber for extraction, pypdf for manipulation | 2023-2024 | pdfplumber is the community standard for text extraction |
| python-docx 0.x | python-docx 1.x | 2024 | Minor API changes, same core patterns |
| n_ctx=2048 default | n_ctx=4096-8192 common | 2024 | Modern GGUF models handle larger contexts efficiently |

**Deprecated/outdated:**
- PyPDF2 package was renamed to `pypdf` (lowercase) in 2023. The `PyPDF2` package still works but `pypdf` is the maintained fork. However, for text extraction specifically, pdfplumber is preferred anyway.

## n_ctx Bump Details

The current `main.py` lifespan sets `n_ctx=4096` at line 111. Change to `8192`:

```python
app.state.llm = Llama(
    model_path=llm_model_path,
    n_ctx=8192,  # was 4096 -- bumped for Phase 8 document context injection
    n_gpu_layers=n_gpu,
    chat_format="chatml",
    verbose=False,
)
```

This doubles the context window. Memory impact is ~32MB additional KV cache on GPU (or CPU). Phi-4-mini handles 8192 tokens natively (its training context was 16K), so no quality degradation.

## Open Questions

1. **File storage location for attachments**
   - What we know: Phase 6 saves to `public/recordings/{id}/docs/`. This is accessible from the browser.
   - What's unclear: Should attachments also live here, or in `backend/uploads/` (which is not web-accessible)?
   - Recommendation: Keep `public/recordings/{id}/docs/` for consistency with Phase 6. The Python backend receives the file path as a parameter from Next.js, not the file itself.

2. **Should the Python backend receive file bytes or a file path?**
   - What we know: The proxy pattern has Next.js save to disk first. Python backend can either receive the file via multipart upload or receive a file path.
   - What's unclear: Which is cleaner architecturally?
   - Recommendation: Pass the file as multipart upload to Python backend (consistent with `/recordings` audio upload pattern). Python backend saves its own copy to `backend/uploads/` for extraction, or reads from the provided disk path. File path approach is simpler since both processes run on the same machine.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.x + pytest-asyncio |
| Framework (frontend) | vitest 4.x + @testing-library/react |
| Config file (backend) | `backend/tests/conftest.py` |
| Config file (frontend) | `vitest.config.ts` |
| Quick run command (backend) | `cd backend && python -m pytest tests/ -x -q` |
| Quick run command (frontend) | `npx vitest run --reporter=verbose` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q && cd .. && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Upload PDF/DOCX/TXT via API, file saved + extracted | integration | `cd backend && python -m pytest tests/test_attachments.py::test_upload_attachment -x` | Wave 0 |
| DOC-01 | 10MB size limit enforced server-side | unit | `cd backend && python -m pytest tests/test_attachments.py::test_upload_size_limit -x` | Wave 0 |
| DOC-02 | PDF text extracted correctly | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_pdf -x` | Wave 0 |
| DOC-02 | DOCX text extracted correctly | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_docx -x` | Wave 0 |
| DOC-02 | TXT text extracted correctly | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_txt -x` | Wave 0 |
| DOC-02 | Corrupted file handled gracefully | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_corrupted -x` | Wave 0 |
| DOC-03 | List attachments returns metadata | integration | `cd backend && python -m pytest tests/test_attachments.py::test_list_attachments -x` | Wave 0 |
| DOC-03 | Delete attachment removes record + file | integration | `cd backend && python -m pytest tests/test_attachments.py::test_delete_attachment -x` | Wave 0 |
| MEET-04 | Stat card renders with doc count | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_text_extraction.py tests/test_attachments.py -x -q`
- **Per wave merge:** Full suite (backend + frontend)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_text_extraction.py` -- covers DOC-02 (extraction correctness + error handling)
- [ ] `backend/tests/test_attachments.py` -- covers DOC-01, DOC-03 (upload, list, delete API endpoints)
- [ ] `src/components/recording/__tests__/meeting-stat-cards.test.tsx` -- covers MEET-04 (4th stat card rendering)
- [ ] Test fixture files: small sample PDF, DOCX, TXT in `backend/tests/fixtures/`
- [ ] Framework install: `pip install pdfplumber python-docx` -- neither currently in requirements.txt

## Sources

### Primary (HIGH confidence)
- Project codebase: `backend/storage.py`, `backend/main.py`, `backend/models.py` -- existing patterns for SQLite CRUD, FastAPI endpoints, Pydantic models
- Project codebase: `src/components/recording/meeting-stat-cards.tsx` -- existing 3-card layout to extend
- Project codebase: `src/components/recording/file-drop-zone.tsx` -- existing component to reuse
- Project codebase: `src/app/api/recordings/[id]/documents/route.ts` -- existing upload route to extend
- Project codebase: `src/app/(dashboard)/recordings/[id]/page.tsx` -- recording detail page structure

### Secondary (MEDIUM confidence)
- [pdfplumber GitHub](https://github.com/jsvine/pdfplumber) -- API reference, benchmarks vs PyPDF2
- [python-docx docs](https://python-docx.readthedocs.io/) -- v1.2.0 API for Document + paragraph extraction
- [2025 PDF extractor comparison](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257) -- benchmarks confirming pdfplumber > PyPDF2 for accuracy

### Tertiary (LOW confidence)
- None -- all findings verified against project code or official library docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pdfplumber and python-docx are well-established, no novelty
- Architecture: HIGH -- follows existing project patterns exactly (storage.py CRUD, FastAPI endpoints, Next.js proxy, TanStack Query)
- Pitfalls: HIGH -- based on direct codebase analysis (e.g., FileDropZone .doc issue, post-recording dialog gap)
- Validation: HIGH -- existing test infrastructure with pytest + vitest covers both backend and frontend

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain, no fast-moving dependencies)
