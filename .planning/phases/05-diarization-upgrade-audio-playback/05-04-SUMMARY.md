---
phase: 05-diarization-upgrade-audio-playback
plan: 04
subsystem: ui
tags: [audio-sync, transcript, zustand, scroll, seek]

requires:
  - phase: 05
    plan: 03
    provides: AudioPlayerBar, Zustand audio playback store

provides:
  - Active utterance highlighting during audio playback (indigo tint)
  - Binary search active utterance detection on timeupdate
  - Click-to-seek on utterance bubbles via seekGeneration store pattern
  - Auto-scroll with manual override and Resume follow button
  - Portal-based player bar layout inside SidebarInset
---

## What was built

Wired transcript-audio synchronization: the active utterance is highlighted with a soft indigo tint during playback, the transcript auto-scrolls to keep the active utterance visible, and clicking any utterance bubble seeks audio to that timestamp and starts playback.

## Key decisions

- **seekGeneration pattern**: Added a `seekGeneration` counter to the Zustand store to distinguish user-initiated seeks from timeupdate reports. The audio element syncs `currentTime` only when the generation increments, fixing click-to-seek.
- **Portal into #player-portal**: Instead of `fixed` positioning (which escapes the sidebar layout), the player bar portals into a `#player-portal` div inside `SidebarInset`. This keeps it naturally bounded by the content area width.
- **Layout restructure**: `SidebarInset` became `h-svh` flex column with `<main>` as `overflow-y-auto flex-1`, so the player bar sits at the bottom of the content area without overlapping.

## Key files

### Created
- (none — all modifications to existing files)

### Modified
- `src/stores/audio-playback.ts` — added `seekGeneration` field and updated `seek()` action
- `src/components/audio/audio-player-bar.tsx` — portal to #player-portal, seekGeneration sync effect
- `src/components/transcript/transcript-view.tsx` — auto-scroll, manual override, Resume follow, click-to-seek wiring
- `src/components/transcript/utterance-bubble.tsx` — playback highlight styling, onSeek prop, cursor-pointer
- `src/app/(dashboard)/layout.tsx` — h-svh SidebarInset, overflow-y-auto main, #player-portal div
- `src/app/(dashboard)/recordings/[id]/page.tsx` — pass utterances to AudioPlayerBar, removed pb-20 hack

## Bug fixes during verification

- **Transcript not loading**: Transcripts were fetched live from backend on every page load. Added local SQLite caching (`transcript_data` column) so transcripts load instantly after first fetch.
- **Speaker stats all zeros**: Old recordings had incomplete speaker stats. Added backend startup migration to recompute extended stats from existing segments.
- **Audio unavailable without backend**: Added fallback to serve local `.webm` file when backend is down.
- **Player bar full-width**: Replaced `fixed` positioning with portal-based layout inside `SidebarInset` flex column.

## Self-Check: PASSED
- [x] Active utterance highlighted during playback
- [x] Auto-scroll keeps active utterance visible
- [x] Manual scroll disables auto-scroll, Resume follow button appears
- [x] Click-to-seek works on utterance bubbles
- [x] Player bar stays at bottom of content area, respects sidebar
- [x] User verified all behaviors
