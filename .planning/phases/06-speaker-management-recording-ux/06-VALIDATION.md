---
phase: 6
slug: speaker-management-recording-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.0.18 + React Testing Library 16.3.2 |
| **Config file** | `vitest.config.ts` |
| **Quick run command** | `npx vitest run --reporter=verbose` |
| **Full suite command** | `npx vitest run --reporter=verbose` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npx vitest run --reporter=verbose`
- **After every plan wave:** Run `npx vitest run --reporter=verbose`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SPKR-01 | unit | `npx vitest run src/components/transcript/__tests__/speaker-stats-panel.test.tsx -x` | No -- Wave 0 | ⬜ pending |
| 06-01-02 | 01 | 1 | SPKR-01 | unit | `npx vitest run src/hooks/__tests__/use-speaker-update.test.ts -x` | No -- Wave 0 | ⬜ pending |
| 06-01-03 | 01 | 1 | SPKR-02 | unit | `npx vitest run src/components/transcript/__tests__/utterance-bubble.test.tsx -x` | Yes (extend) | ⬜ pending |
| 06-02-01 | 02 | 2 | RUX-01 | unit | `npx vitest run src/components/recording/__tests__/post-recording-dialog.test.tsx -x` | No -- Wave 0 | ⬜ pending |
| 06-02-02 | 02 | 2 | RUX-02 | unit | `npx vitest run src/components/recording/__tests__/post-recording-dialog.test.tsx -x` | No -- Wave 0 | ⬜ pending |
| 06-02-03 | 02 | 2 | RUX-03 | unit | `npx vitest run src/components/recording/__tests__/post-recording-dialog.test.tsx -x` | No -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/components/transcript/__tests__/speaker-stats-panel.test.tsx` — stubs for SPKR-01, SPKR-02 inline edit
- [ ] `src/components/recording/__tests__/post-recording-dialog.test.tsx` — stubs for RUX-01, RUX-02, RUX-03
- [ ] `src/components/transcript/__tests__/inline-edit.test.tsx` — stubs for reusable inline edit component
- [ ] Extend `src/components/transcript/__tests__/utterance-bubble.test.tsx` — add role display tests

*Existing infrastructure covers framework installation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dialog opens after recording stops | RUX-01 | Requires MediaRecorder + real audio capture | 1. Click record FAB 2. Record 3s 3. Click stop 4. Verify dialog appears |
| Background processing status updates | RUX-03 | Requires real backend transcription pipeline | 1. Stop recording 2. Verify "Transcribing..." in dialog 3. Wait for completion 4. Verify status updates |
| Speaker rename propagates to all bubbles | SPKR-01 | Visual verification of propagation across scroll | 1. Rename speaker in stats panel 2. Scroll transcript 3. Verify all bubbles show new name |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
