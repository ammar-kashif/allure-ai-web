---
phase: 7
slug: document-attachments
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.x + pytest-asyncio |
| **Framework (frontend)** | vitest 4.x + @testing-library/react |
| **Config file (backend)** | `backend/tests/conftest.py` |
| **Config file (frontend)** | `vitest.config.ts` |
| **Quick run command (backend)** | `cd backend && python -m pytest tests/ -x -q` |
| **Quick run command (frontend)** | `npx vitest run --reporter=verbose` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q && cd .. && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** `cd backend && python -m pytest tests/test_text_extraction.py tests/test_attachments.py -x -q`
- **After every plan wave:** `cd backend && python -m pytest tests/ -x -q && cd .. && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | DOC-02 | unit | `cd backend && python -m pytest tests/test_text_extraction.py -x` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 0 | DOC-01, DOC-03 | integration | `cd backend && python -m pytest tests/test_attachments.py -x` | ❌ W0 | ⬜ pending |
| 7-01-03 | 01 | 0 | MEET-04 | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | DOC-01 | integration | `cd backend && python -m pytest tests/test_attachments.py::test_upload_attachment -x` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 1 | DOC-01 | unit | `cd backend && python -m pytest tests/test_attachments.py::test_upload_size_limit -x` | ❌ W0 | ⬜ pending |
| 7-02-03 | 02 | 1 | DOC-02 | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_pdf -x` | ❌ W0 | ⬜ pending |
| 7-02-04 | 02 | 1 | DOC-02 | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_docx -x` | ❌ W0 | ⬜ pending |
| 7-02-05 | 02 | 1 | DOC-02 | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_txt -x` | ❌ W0 | ⬜ pending |
| 7-02-06 | 02 | 1 | DOC-02 | unit | `cd backend && python -m pytest tests/test_text_extraction.py::test_extract_corrupted -x` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 1 | DOC-03 | integration | `cd backend && python -m pytest tests/test_attachments.py::test_list_attachments -x` | ❌ W0 | ⬜ pending |
| 7-03-02 | 03 | 1 | DOC-03 | integration | `cd backend && python -m pytest tests/test_attachments.py::test_delete_attachment -x` | ❌ W0 | ⬜ pending |
| 7-03-03 | 03 | 1 | MEET-04 | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_text_extraction.py` — stubs for DOC-02 (extraction correctness + error handling)
- [ ] `backend/tests/test_attachments.py` — stubs for DOC-01, DOC-03 (upload, list, delete API endpoints)
- [ ] `src/components/recording/__tests__/meeting-stat-cards.test.tsx` — stubs for MEET-04 (4th stat card rendering)
- [ ] Test fixture files: small sample PDF, DOCX, TXT in `backend/tests/fixtures/`
- [ ] Framework install: `pip install pdfplumber python-docx` — neither currently in requirements.txt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| File picker opens on button click | DOC-01 | Browser file dialog | Click "+ Upload documents", verify file picker opens with PDF/DOCX/TXT filter |
| Drag-and-drop onto FileDropZone | DOC-01 | Browser drag event | Drag a PDF onto the drop zone, verify upload starts |
| Delete confirmation dialog | DOC-03 | UI interaction flow | Click X on attachment, verify confirmation dialog, confirm delete |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

