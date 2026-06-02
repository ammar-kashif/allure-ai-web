---
phase: 02-ai-extraction-and-promotion
plan: 03
subsystem: ui
tags: [react, outcomes, tabs, evidence-highlight, promotion, shadcn, vitest]

# Dependency graph
requires:
  - phase: 02-01
    provides: "Backend extraction endpoints, outcome types, promote API"
  - phase: 02-02
    provides: "Frontend hooks (useOutcomes, usePromoteOutcome), evidence-highlight store, outcome types"
provides:
  - "Outcomes tab UI with grouped outcome cards, confidence coloring, and summary banner"
  - "Evidence cross-navigation from outcome cards to transcript with yellow highlight"
  - "One-click promotion of action items and requirements with toast feedback"
  - "Tabbed recording detail page (Info, Transcript, Outcomes)"
  - "Component tests for OutcomesTab and OutcomeCard"
affects: [03-task-management, 04-document-generation-and-demo-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: [evidence-highlight-store, tab-controlled-navigation, confidence-coloring]

key-files:
  created:
    - src/components/outcome/outcomes-tab.tsx
    - src/components/outcome/outcome-card.tsx
    - src/components/outcome/outcome-section.tsx
    - src/components/outcome/summary-banner.tsx
    - src/components/outcome/__tests__/outcomes-tab.test.tsx
    - src/components/outcome/__tests__/outcome-card.test.tsx
  modified:
    - src/app/(dashboard)/recordings/[id]/page.tsx
    - src/components/transcript/transcript-view.tsx
    - src/components/transcript/utterance-bubble.tsx

key-decisions:
  - "Evidence cross-navigation uses zustand store (useEvidenceHighlight) to coordinate tab switch + scroll + highlight"
  - "Confidence threshold 0.80 for green/amber coloring with 'Needs review' label"
  - "Promote button only on action_item and requirement types; decisions and blockers informational only"

patterns-established:
  - "Evidence highlight pattern: store-driven tab switch + scrollIntoView + CSS transition fade"
  - "Outcome grouping: filter by type, skip empty sections, fixed order (Decisions, Action Items, Requirements, Blockers)"

requirements-completed: [EXT-03, EXT-04, EXT-05, EXT-06, EXT-07]

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 02 Plan 03: Outcomes Tab UI Summary

**Tabbed recording detail page with grouped outcome cards, confidence coloring, evidence cross-navigation with yellow highlight, and one-click promotion**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-15T10:00:00Z
- **Completed:** 2026-03-15T10:08:00Z
- **Tasks:** 3 (2 implementation + 1 human verification)
- **Files modified:** 13

## Accomplishments
- Built complete Outcomes tab with summary banner (total count, type breakdown, review count) and collapsible sections grouped by outcome type
- Outcome cards with confidence-based coloring (green >= 0.80, amber < 0.80 with "Needs review" label) and promote functionality for action items and requirements
- Evidence cross-navigation: clicking evidence link switches to Transcript tab, scrolls to utterance, highlights yellow for 3 seconds
- Recording detail page upgraded to tabbed layout (Info, Transcript, Outcomes) controlled via evidence-highlight store
- Component tests covering rendering states, confidence coloring, promote button visibility, and loading/error states

## Task Commits

Each task was committed atomically:

1. **Task 1: Outcome components and recording detail page with tabs** - `1c9b279` (feat) + `f6c05f0` (fix: test mock)
2. **Task 2: Evidence cross-navigation and transcript highlight** - (included in 1c9b279, no additional changes needed)
3. **Task 3: Human verification** - Checkpoint approved, no code changes

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/components/outcome/outcomes-tab.tsx` - Tab container with summary banner, grouped sections, loading/error states
- `src/components/outcome/outcome-card.tsx` - Individual outcome card with confidence coloring, evidence link, promote button
- `src/components/outcome/outcome-section.tsx` - Collapsible section per outcome type with count in header
- `src/components/outcome/summary-banner.tsx` - Stats banner: total outcomes, type breakdown, items needing review
- `src/components/outcome/__tests__/outcomes-tab.test.tsx` - Tests for OutcomesTab rendering states
- `src/components/outcome/__tests__/outcome-card.test.tsx` - Tests for OutcomeCard confidence coloring and promote visibility
- `src/app/(dashboard)/recordings/[id]/page.tsx` - Added tabbed layout with Info/Transcript/Outcomes tabs
- `src/components/transcript/transcript-view.tsx` - Added highlight scrolling via evidence-highlight store
- `src/components/transcript/utterance-bubble.tsx` - Added yellow highlight prop with CSS transition fade

## Decisions Made
- Evidence cross-navigation implemented via zustand store (useEvidenceHighlight) coordinating tab switch, scroll, and highlight in one action
- Confidence threshold at 0.80 separates green (high confidence) from amber (needs review) styling
- Promote button restricted to action_item and requirement types only; decisions and blockers are informational
- Task 2 (evidence cross-navigation) was already implemented as part of Task 1's commit, requiring no additional changes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing useExtract mock in outcomes-tab test**
- **Found during:** Task 1 (test verification)
- **Issue:** Test failed because useExtractionStatus hook was not mocked
- **Fix:** Added vi.mock for the extraction status hook
- **Files modified:** src/components/outcome/__tests__/outcomes-tab.test.tsx
- **Verification:** All component tests pass
- **Committed in:** f6c05f0

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Minor test fix, no scope creep.

## Issues Encountered
None beyond the test mock fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AI extraction UI complete, ready for Phase 3 (Task Management) and Phase 4 (Document Generation)
- Evidence cross-navigation pattern established and reusable for future deep-linking features

## Self-Check: PASSED

- All 6 created files verified on disk
- Commits 1c9b279 and f6c05f0 verified in git history

---
*Phase: 02-ai-extraction-and-promotion*
*Completed: 2026-03-15*

