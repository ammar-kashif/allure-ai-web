---
phase: 8
slug: context-aware-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | backend/tests/ directory structure, pytest discovery |
| **Quick run command** | `cd backend && python -m pytest tests/test_document_generation.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_document_generation.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | GEN-01 | unit | `cd backend && python -m pytest tests/test_document_generation.py -x -q -k "diagram"` | Stubs only | ⬜ pending |
| 08-01-02 | 01 | 1 | GEN-03 | unit | `cd backend && python -m pytest tests/test_document_generation.py -x -q -k "prd"` | Stubs only | ⬜ pending |
| 08-02-01 | 02 | 1 | GEN-02 | unit | `cd backend && python -m pytest tests/test_document_generation.py -x -q -k "context"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_document_generation.py` — replace skip stubs with real tests for prompt content, context injection, truncation logic
- [ ] New test for `build_document_context()` function — truncation, empty docs filtering, multi-doc budget splitting
- [ ] New test for `get_attachments_with_text()` storage query
- [ ] Tests should mock LLM calls (no actual model needed) — verify prompt construction, not LLM output

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mermaid diagrams model the product/system, not the meeting flow | GEN-01 | Requires visual inspection of generated diagrams | Generate diagram with sample transcript; verify it shows system architecture, not meeting steps |
| PRD output quality improvement | GEN-03 | Subjective quality assessment | Compare PRD output before/after prompt changes with same transcript |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
