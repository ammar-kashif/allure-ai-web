---
phase: 9
slug: integration-hardening-tech-debt
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | SPKR-01, SPKR-02 | unit | `cd backend && python -m pytest tests/test_models_speaker_stats.py -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | RUX-02, DOC-02 | integration | Manual — requires running backend | N/A | ⬜ pending |
| 09-01-03 | 01 | 1 | GEN-02 | integration | Manual — end-to-end flow | N/A | ⬜ pending |
| 09-01-04 | 01 | 1 | DOC-02 | unit/lint | `cd backend && python -c "import ast; [exit(1) for n in ast.walk(ast.parse(open('document_generation.py').read())) if isinstance(n,(ast.Import,ast.ImportFrom)) and n.col_offset>0]"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_models_speaker_stats.py` — unit test: SpeakerStats model with custom_label/role fields validates correctly, defaults work for backward compat
- [ ] Verify existing tests still pass after import move (no new test file needed)

*Existing infrastructure covers lint/import checks via inline script.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Documents forwarded when backendId delayed | RUX-02, DOC-02 | Requires running backend + timing-dependent race condition | 1. Start recording 2. Stop recording 3. Immediately save dialog with documents 4. Verify documents appear in backend extraction results |
| Document context available for generation | GEN-02 | End-to-end flow requiring live backend | 1. Upload docs via post-recording dialog 2. Trigger generation 3. Verify document text appears in generation context |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
