---
phase: 4
slug: document-generation-and-demo-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 4.x (frontend), pytest (backend) |
| **Config file** | vitest.config.ts, backend/tests/conftest.py |
| **Quick run command** | `npm test` |
| **Full suite command** | `npm test && cd backend && python -m pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm test`
- **After every plan wave:** Run `npm test && cd backend && python -m pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | DOC-01 | unit | `npm test -- src/lib/db/documents.test.ts` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | DOC-01 | integration | `npm test -- src/app/api/documents` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | DOC-02 | integration | `cd backend && python -m pytest tests/test_document_generation.py` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | DOC-03 | unit | `npm test -- src/components/document/mermaid-diagram.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/lib/db/documents.test.ts` — stubs for DOC-01 (CRUD operations)
- [ ] `src/app/api/documents/__tests__/route.test.ts` — stubs for DOC-01 (API routes)
- [ ] `backend/tests/test_document_generation.py` — stubs for DOC-02 (Mermaid generation)
- [ ] Documents table added to `schema.sql` — required before any tests run

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mermaid diagrams render visually correct SVG | DOC-03 | Visual correctness cannot be automated | Generate diagram, verify SVG renders in browser without overlapping nodes |
| PRD markdown renders with correct styling | DOC-01 | Visual styling check | Generate PRD, verify headings/lists/sections display correctly |
| Dashboard stat card displays document count | DOC-01 | UI layout verification | Generate a document, navigate to dashboard, verify 4th stat card shows count |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

