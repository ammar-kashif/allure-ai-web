# Phase 7: Document Attachments - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can upload PDF, DOCX, and TXT documents to recordings, with text automatically extracted and stored for downstream generation (Phase 8). Attached documents are listed on the recording detail page with an upload action, and the meeting stat cards show a document count. The llama.cpp n_ctx is bumped to 8192 to prepare for Phase 8's context injection. Document-aware generation itself is Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Text Extraction
- Extraction runs on the Python backend (FastAPI) — consistent with STT/diarization processing
- Libraries: PyPDF2 or pdfplumber for PDF, python-docx for DOCX, plain read for TXT
- Extraction is synchronous during the upload request — PDF/DOCX parsing is sub-second, no job queue needed
- Supported file types: PDF, DOCX, TXT (drop .doc legacy support)
- n_ctx increased to 8192 in this phase to unblock Phase 8 document context injection

### Document Display
- Attached documents shown in an "Attached Documents" card inside the Info tab on the recording detail page
- Card sits below the existing Recording Info card
- Each document row shows: file type icon, filename, file size
- No text preview snippet — just filename and size
- Users can delete attached documents with an X button + confirmation
- MEET-04: New 4th stat card "Attached Documents" alongside Duration, Processing Time, Speakers

### Upload from Detail Page
- "+ Upload documents" button inside the Attached Documents card in the Info tab
- Clicking opens file picker; reuses FileDropZone component from Phase 6
- Upload flow: Next.js API route receives file → saves to disk → calls Python backend for text extraction → stores metadata + extracted text in backend DB
- Post-recording dialog upload path updated to also trigger text extraction and DB storage (consistent behavior regardless of upload source)

### Storage & Metadata
- New `attachments` table in Python backend SQLite (allure.db), alongside existing `jobs` table
- Schema: id, recording_id, filename, file_type, file_size, extracted_text, created_at
- Extracted text stored in same row as attachment metadata (single table, no joins)
- 10 MB per-file size limit — validated client-side and server-side
- List endpoint (GET /recordings/{id}/attachments) returns metadata only (no extracted text) — text retrieved separately when Phase 8 needs it

### Claude's Discretion
- Exact Python extraction library choice (PyPDF2 vs pdfplumber)
- Backend API endpoint design (upload, list, delete, get-text)
- FileDropZone integration pattern on detail page (inline expand vs modal)
- Error handling for extraction failures (corrupted PDFs, empty docs)
- Stat card icon and styling for "Attached Documents"
- How n_ctx bump is configured in llama.cpp settings

</decisions>

<specifics>
## Specific Ideas

- Reuse FileDropZone from post-recording dialog for consistent upload UX across both entry points
- Document card in Info tab follows the same rounded-xl bg-card shadow-card pattern as Recording Info card
- Both post-recording dialog and detail page uploads feed into the same backend extraction + storage pipeline
- Metadata-only list API keeps the recording detail page fast even with many attachments

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FileDropZone` component (`file-drop-zone.tsx`): Drag-and-drop with file list, accepts PDF/DOCX/DOC/TXT — update to remove DOC, add size validation
- `PostRecordingDialog` (`post-recording-dialog.tsx`): Already uploads files via `POST /api/recordings/{id}/documents` — update to trigger extraction
- `MeetingStatCards` component: Shows 3 cards (duration, processing time, speakers) — add 4th card for doc count
- `Dialog` and `Button` from shadcn/ui for delete confirmation

### Established Patterns
- Next.js API routes proxy all backend calls (recordings, transcripts, outcomes)
- Backend SQLite via `storage.py` with `_get_conn()` pattern for connection management
- TanStack Query mutations for data persistence with optimistic updates
- Sonner toast notifications for async feedback
- File storage in `public/recordings/{id}/docs/` directory

### Integration Points
- `POST /api/recordings/[id]/documents/route.ts`: Currently filesystem-only — extend to call Python backend for extraction + DB storage
- `backend/storage.py`: Add `attachments` table to `init_db()`, CRUD functions for attachments
- `backend/main.py`: New endpoints for upload-with-extraction, list attachments, delete attachment
- Recording detail page (`recordings/[id]/page.tsx`): Add Attached Documents card to Info tab
- `MeetingStatCards`: Add docCount prop and 4th stat card
- `backend/main.py` or config: Bump n_ctx to 8192

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-document-attachments*
*Context gathered: 2026-03-19*

