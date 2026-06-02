---
phase: 1
slug: recording-and-transcription-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest ^3.0 + React Testing Library ^16.0 |
| **Config file** | `vitest.config.ts` — created by Wave 0 (Plan 01-00) |
| **Quick run command** | `npx vitest run --reporter=verbose` |
| **Full suite command** | `npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npx vitest run --reporter=verbose`
- **After every plan wave:** Run `npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-00-01 | 00 | 0 | ALL | infra | `npx vitest run --reporter=verbose` | Plan 01-00 creates | ⬜ pending |
| 01-01-02 | 01 | 1 | REC-01, REC-02, REC-03 | unit | `npx vitest run src/hooks/__tests__/use-audio-recorder.test.ts src/lib/audio/__tests__/chunk-store.test.ts src/components/recording/__tests__/recording-fab.test.tsx` | Plan 01-00 skeleton, Plan 01-01 fills | ⬜ pending |
| 01-02-01 | 02 | 2 | STT-01 | unit | `npx vitest run src/app/api/recordings/__tests__/route.test.ts` | Plan 01-00 skeleton, Plan 01-02 fills | ⬜ pending |
| 01-02-02 | 02 | 2 | STT-04, REC-06 | unit | `npx vitest run src/hooks/__tests__/use-recordings.test.ts` | Plan 01-00 skeleton, Plan 01-02 fills | ⬜ pending |
| 01-03-01 | 03 | 2 | REC-04, REC-05 | integration | `npx vitest run src/components/recording/__tests__/recording-hub.test.tsx src/components/recording/__tests__/project-assignment.test.tsx` | Plan 01-00 skeleton, Plan 01-03 fills | ⬜ pending |
| 01-03-02 | 03 | 2 | REC-01 | unit | `npx vitest run src/hooks/__tests__/use-audio-recorder.test.ts` | Plan 01-00 skeleton, Plan 01-03 updates | ⬜ pending |
| 01-04-01 | 04 | 3 | STT-02, STT-03 | integration | `npx vitest run src/components/transcript/__tests__/transcript-view.test.tsx src/components/transcript/__tests__/utterance-bubble.test.tsx` | Plan 01-00 skeleton, Plan 01-04 fills | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `vitest.config.ts` — Vitest configuration with happy-dom environment (Plan 01-00 Task 1)
- [x] `src/test/setup.ts` — Test setup file (MSW handlers, IndexedDB mock via fake-indexeddb) (Plan 01-00 Task 1)
- [x] Framework install: `npm install -D vitest @testing-library/react @testing-library/jest-dom @vitejs/plugin-react happy-dom msw fake-indexeddb` (Plan 01-01 Task 1)
- [x] `fake-indexeddb` — Required for testing IndexedDB operations (chunk-store tests)
- [x] MSW (Mock Service Worker) — Required for mocking API route responses in tests
- [x] All 9 test skeleton files created (Plan 01-00 Task 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Microphone permission prompt appears | REC-02 | Browser permission API cannot be automated in unit tests | 1. Open app 2. Click FAB 3. Verify browser mic permission dialog appears |
| Recording continues during page navigation | REC-01 | Requires real browser navigation and MediaRecorder lifecycle | 1. Start recording 2. Navigate to another page 3. Verify FAB still shows recording state 4. Stop recording 5. Verify recording saved |
| Crash recovery restores audio | REC-03 | Requires simulating browser crash (kill process) | 1. Start recording 2. Wait 10+ seconds 3. Force kill browser tab 4. Reopen app 5. Verify recovery prompt or auto-recovered recording |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved

