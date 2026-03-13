---
phase: 3
slug: task-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.x + happy-dom + @testing-library/react |
| **Config file** | vitest.config.ts |
| **Quick run command** | `npm test` |
| **Full suite command** | `npm test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm test`
- **After every plan wave:** Run `npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TASK-01 | unit | `npx vitest run src/app/api/tasks/__tests__/route.test.ts` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TASK-02 | unit | `npx vitest run src/app/api/tasks/__tests__/route.test.ts` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TASK-03 | unit | `npx vitest run src/app/api/tasks/__tests__/route.test.ts` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | TASK-04 | unit | `npx vitest run src/components/task/__tests__/task-kanban-view.test.tsx` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | TASK-05 | unit | `npx vitest run src/components/task/__tests__/task-kanban-view.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/app/api/tasks/__tests__/route.test.ts` — stubs for TASK-01, TASK-02, TASK-03 (API CRUD + filtering)
- [ ] `src/components/task/__tests__/task-kanban-view.test.tsx` — stubs for TASK-04, TASK-05 (Kanban rendering + DnD)
- [ ] No new framework install needed — Vitest + Testing Library already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Kanban drag-and-drop visual feedback | TASK-05 | DragOverlay visual rendering requires real browser | 1. Open /tasks, switch to Board view. 2. Drag a card from "To Do" to "In Progress". 3. Verify card appears in new column and status updates. |
| Sheet side panel animation | TASK-01 | CSS transition timing | 1. Click a task row. 2. Verify Sheet slides in from right. 3. Close and verify smooth close animation. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
