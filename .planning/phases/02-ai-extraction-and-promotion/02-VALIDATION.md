---
phase: 2
slug: ai-extraction-and-promotion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | Vitest 4.x + happy-dom |
| **Framework (backend)** | pytest 8.x + pytest-asyncio |
| **Config file (frontend)** | vitest.config.ts |
| **Config file (backend)** | backend/pyproject.toml [tool.pytest.ini_options] |
| **Quick run command (frontend)** | `npx vitest run --reporter=verbose` |
| **Quick run command (backend)** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `npx vitest run && cd backend && python -m pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** `npx vitest run --reporter=verbose` (frontend) + `cd backend && python -m pytest tests/ -x -q` (backend)
- **After every plan wave:** Full suite across both frontend and backend
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | EXT-01 | unit (backend) | `cd backend && python -m pytest tests/test_extraction.py::test_extraction_produces_outcomes -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | EXT-02 | unit (backend) | `cd backend && python -m pytest tests/test_extraction.py::test_outcome_schema_validation -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | EXT-03 | unit (frontend) | `npx vitest run src/components/outcome/__tests__/outcomes-tab.test.tsx` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | EXT-04 | unit (frontend) | `npx vitest run src/components/outcome/__tests__/outcome-card.test.tsx` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | EXT-05 | integration | `cd backend && python -m pytest tests/test_api.py::test_promote_action_item -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | EXT-06 | integration | `cd backend && python -m pytest tests/test_api.py::test_promote_requirement -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 0 | EXT-07 | unit (backend) | `cd backend && python -m pytest tests/test_extraction.py::test_backlink_format -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_extraction.py` — stubs for EXT-01, EXT-02, EXT-07 (mock LLM, test schema validation and backlink format)
- [ ] `src/components/outcome/__tests__/outcomes-tab.test.tsx` — stubs for EXT-03
- [ ] `src/components/outcome/__tests__/outcome-card.test.tsx` — stubs for EXT-04
- [ ] `backend/tests/test_api.py` — stubs for EXT-05, EXT-06 (promotion endpoints)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Extraction quality with real transcript | EXT-01 | LLM output varies; mocked in automated tests | Run extraction on a sample transcript, verify outcomes are sensible |
| Visual distinction of low-confidence items | EXT-04 | Visual/styling check | Inspect UI: items below 0.80 should show amber badge or dimmed styling |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

