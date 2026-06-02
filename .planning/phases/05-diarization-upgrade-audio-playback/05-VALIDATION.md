---
phase: 5
slug: diarization-upgrade-audio-playback
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | Vitest 4.0.18 + Testing Library |
| **Framework (backend)** | pytest |
| **Config file (frontend)** | `vitest.config.ts` |
| **Config file (backend)** | `backend/tests/` directory |
| **Quick run command (frontend)** | `npx vitest run --reporter=verbose` |
| **Quick run command (backend)** | `cd backend && .venv/bin/python -m pytest tests/ -x -q` |
| **Full suite command** | `npx vitest run && cd backend && .venv/bin/python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command for affected stack (frontend or backend)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DIAR-01 | unit | `cd backend && .venv/bin/python -m pytest tests/test_transcription.py -x -k agglomerative` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | DIAR-02 | unit | `cd backend && .venv/bin/python -m pytest tests/test_transcription.py -x -k auto_speakers` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | SPKR-03 | unit | `cd backend && .venv/bin/python -m pytest tests/test_transcription.py -x -k extended_stats` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | PLAY-01 | integration | `npx vitest run src/components/audio/__tests__/audio-player-bar.test.tsx` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | PLAY-02 | unit | `npx vitest run src/components/transcript/__tests__/transcript-view.test.tsx -t "highlight"` | ⚠️ partial | ⬜ pending |
| 05-02-03 | 02 | 2 | PLAY-03 | unit | `npx vitest run src/components/audio/__tests__/audio-player-bar.test.tsx -t "speed"` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | SPKR-04 | unit | `npx vitest run src/components/transcript/__tests__/utterance-bubble.test.tsx` | ✅ | ⬜ pending |
| 05-03-01 | 03 | 2 | MEET-01 | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 2 | MEET-02 | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx -t "processing"` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 2 | MEET-03 | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx -t "speakers"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_transcription.py` — add tests for AgglomerativeClustering (DIAR-01, DIAR-02) and extended speaker stats (SPKR-03)
- [ ] `src/components/audio/__tests__/audio-player-bar.test.tsx` — covers PLAY-01, PLAY-03
- [ ] `src/components/recording/__tests__/meeting-stat-cards.test.tsx` — covers MEET-01, MEET-02, MEET-03
- [ ] `src/components/transcript/__tests__/transcript-view.test.tsx` — extend for playback highlight tests (PLAY-02)

*Existing infrastructure covers SPKR-04 (utterance-bubble tests exist).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Auto-scroll pauses on manual scroll | PLAY-02 | Scroll behavior hard to test programmatically | Play audio, scroll away manually, verify "Resume follow" button appears |
| WAV seeking works in Safari | PLAY-01 | Browser-specific Range request handling | Open recording in Safari, seek to middle of audio, verify playback resumes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

