---
phase: 05-diarization-upgrade-audio-playback
verified: 2026-03-18T18:30:00Z
status: human_needed
score: 14/14 must-haves verified
human_verification:
  - test: "Play audio and observe utterance highlighting"
    expected: "The currently-playing utterance shows a soft indigo/blue tint (bg-indigo-100/60) and updates as playback progresses"
    why_human: "Requires live audio element and time-update events; cannot verify DOM changes from static analysis"
  - test: "Manually scroll the transcript during playback, then click Resume follow"
    expected: "Auto-scroll pauses and the Resume follow button appears when scrolling away; clicking Resume follow re-enables auto-scroll and snaps back to active utterance"
    why_human: "Requires real scroll event interaction and DOM state changes"
  - test: "Click any utterance bubble"
    expected: "Audio seeks to that utterance's start time and begins playing"
    why_human: "Requires live audio seek interaction"
  - test: "Change speed to 2x via the speed selector dropdown"
    expected: "Audio plays at 2x speed; dropdown shows 2x; other speeds (0.5x, 1x, 1.5x) remain selectable"
    why_human: "Requires live audio element playbackRate verification"
  - test: "Verify audio player bar positioning"
    expected: "Player bar appears at the bottom of the SidebarInset content area, not overlapping sidebar, with correct width"
    why_human: "Portal-based layout requires visual inspection to confirm correct placement"
  - test: "Switch from Transcript tab to Outcomes tab during playback"
    expected: "Player bar remains visible; no utterance highlighting occurs on non-transcript tabs; switching back to Transcript tab resumes highlighting"
    why_human: "Requires live tab-switching with active audio playback"
---

# Phase 5: Diarization Upgrade & Audio Playback Verification Report

**Phase Goal:** Users can play back meeting audio synced to the transcript with active line highlighting, and see enriched speaker and meeting statistics powered by improved diarization
**Verified:** 2026-03-18T18:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Backend uses AgglomerativeClustering instead of MeanShift | VERIFIED | `transcription.py:16` imports `AgglomerativeClustering`; `transcription.py:147-153` instantiates with `n_clusters=None, distance_threshold=0.7, metric="cosine", linkage="average"` |
| 2 | Speaker count is auto-detected via distance_threshold | VERIFIED | `n_clusters=None` with `distance_threshold=0.7` in `FastDiarizer.diarize()` |
| 3 | Backend returns extended speaker stats (10 fields) | VERIFIED | `calculate_speaker_stats` returns all 10 fields: `label, talk_time_pct, utterance_count, talk_time, word_count, wpm, turns, avg_turn_duration, pauses, avg_pause_duration` (lines 340-353) |
| 4 | Backend returns processing_time in transcript response | VERIFIED | `run_transcription` wraps pipeline with `time.perf_counter()` and returns `"processing_time": processing_time` (lines 385, 431-439) |
| 5 | Browser can stream WAV audio with seek support | VERIFIED | `audio/route.ts` forwards Range headers, sets `Accept-Ranges: bytes`, streams response body from backend |
| 6 | TypeScript types exist for extended transcript data | VERIFIED | `recording.ts` exports `SpeakerStat` (10 fields) and extended `Transcript` with `speakers?, duration?, processingTime?` |
| 7 | Zustand audio playback store manages all required state | VERIFIED | `audio-playback.ts` has all state (`isPlaying, currentTime, duration, playbackRate, activeUtteranceIndex, autoScrollEnabled, seekGeneration`) and all actions |
| 8 | Speaker names render as colored badge/pill components | VERIFIED | `speaker-badge.tsx` renders `rounded-full` span using `colors.badge` from shared palette |
| 9 | Speaker colors are consistent via single source of truth | VERIFIED | `speakerColors` and `getSpeakerIndex` exported from `utterance-bubble.tsx`; `speaker-badge.tsx` imports from there |
| 10 | User can play and pause meeting audio from the recording detail page | VERIFIED | `audio-player-bar.tsx` has Play/Pause button toggling `useAudioPlayback.togglePlayback()`; `page.tsx` renders `<AudioPlayerBar recordingId={id} utterances={transcript?.utterances} />` |
| 11 | User can change playback speed to 0.5x, 1x, 1.5x, or 2x | VERIFIED | `speed-selector.tsx` with `SPEED_OPTIONS = [0.5, 1, 1.5, 2]`; wired to `setPlaybackRate` and `audio.playbackRate` in player bar |
| 12 | User sees meeting duration, processing time, and speaker count as cards above tab bar | VERIFIED | `meeting-stat-cards.tsx` renders 3 cards; placed above `<Tabs>` in `page.tsx` lines 308-312 inside `status === "ready"` block |
| 13 | User sees per-speaker stats panel at top of Transcript tab | VERIFIED | `speaker-stats-panel.tsx` with 8 metric cells per speaker; rendered in `TabsContent value="transcript"` above `TranscriptView` (page.tsx lines 358-361) |
| 14 | Audio player is visible across all tabs | VERIFIED | `<AudioPlayerBar>` rendered outside `<Tabs>` (page.tsx line 396); portals into `#player-portal` div in layout.tsx inside `SidebarInset` |

**Score:** 14/14 truths verified (automated)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/transcription.py` | AgglomerativeClustering diarization + extended stats | VERIFIED | Contains `AgglomerativeClustering` at line 147; all 10 stat fields at lines 340-353 |
| `backend/models.py` | Extended SpeakerStats and TranscriptResponse with processing_time | VERIFIED | `SpeakerStats` has all 10 fields; `TranscriptResponse` has `processing_time: float` |
| `backend/main.py` | GET /recordings/{job_id}/audio endpoint | VERIFIED | Endpoint at line 220; uses `FileResponse` with `Accept-Ranges` header |
| `src/app/api/recordings/[id]/audio/route.ts` | Next.js proxy for WAV audio with Range header forwarding | VERIFIED | Forwards `Range` header; streams response body; falls back to local webm |
| `src/app/api/recordings/[id]/transcript/route.ts` | Updated proxy passing through speakers array and processingTime | VERIFIED | `transformBackendData` maps all 10 speaker fields camelCase; includes `duration` and `processingTime` |
| `src/types/recording.ts` | SpeakerStat type + extended Transcript | VERIFIED | `SpeakerStat` interface with 10 fields; `Transcript` extended with `speakers?, duration?, processingTime?` |
| `src/stores/audio-playback.ts` | Zustand store with all state and actions | VERIFIED | 59 lines; exports `useAudioPlayback`; includes `seekGeneration` pattern added in Plan 04 |
| `src/components/transcript/speaker-badge.tsx` | Colored badge/pill for speaker names | VERIFIED | 23 lines; imports `speakerColors, getSpeakerIndex` from `./utterance-bubble`; renders `colors.badge` class |
| `src/components/transcript/utterance-bubble.tsx` | Exports speakerColors, getSpeakerIndex; supports playback highlight and onSeek | VERIFIED | Both exported; `isPlaybackActive` prop adds `bg-indigo-100/60`; `onSeek` prop + `cursor-pointer` wired |
| `src/components/audio/audio-player-bar.tsx` | Sticky bottom player bar (min 80 lines) | VERIFIED | 188 lines; play/pause, seek slider, time display, SpeedSelector; portals into `#player-portal` |
| `src/components/audio/speed-selector.tsx` | Playback speed dropdown (0.5x/1x/1.5x/2x) | VERIFIED | 41 lines; DropdownMenu with all 4 speed options |
| `src/components/recording/meeting-stat-cards.tsx` | Summary cards for duration, processing time, speaker count | VERIFIED | 58 lines; 3 StatCard instances with Clock/Timer/Users icons |
| `src/components/transcript/speaker-stats-panel.tsx` | Collapsible panel with per-speaker stats | VERIFIED | 80 lines; Collapsible with 8 metrics per speaker using SpeakerBadge |
| `src/app/(dashboard)/recordings/[id]/page.tsx` | Wired recording detail page | VERIFIED | Imports and renders all 5 new components in correct positions |
| `src/components/transcript/transcript-view.tsx` | Auto-scroll, Resume follow, click-to-seek (min 60 lines) | VERIFIED | 141 lines; `autoScrollEnabled` guard; `isProgrammaticScroll` ref pattern; Resume follow button; `onSeek` passed to each bubble |
| `src/app/(dashboard)/layout.tsx` | SidebarInset with h-svh flex layout and #player-portal div | VERIFIED | `h-svh` on SidebarInset; `flex-1 overflow-y-auto` on main; `<div id="player-portal" />` at bottom |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `audio/route.ts` | `backend/main.py` | fetch to `/recordings/{backendId}/audio` with Range forwarding | WIRED | Line 29: `${BACKEND_URL}/recordings/${recording.backendId}/audio`; Range header forwarded lines 23-26 |
| `transcript/route.ts` | `backend/main.py` | fetch to `/recordings/{backendId}/transcript`; speakers + processingTime mapped | WIRED | `transformBackendData` maps all fields; `processing_time` → `processingTime` |
| `speaker-badge.tsx` | `utterance-bubble.tsx` | imports `speakerColors` and `getSpeakerIndex` | WIRED | Line 2: `import { speakerColors, getSpeakerIndex } from "./utterance-bubble"` |
| `audio-player-bar.tsx` | `audio-playback.ts` | `useAudioPlayback` for state sync | WIRED | Lines 44-57: all store selectors; `setActiveUtterance` called in `handleTimeUpdate` |
| `audio-player-bar.tsx` | `api/recordings/[id]/audio` | HTMLAudioElement src URL | WIRED | Line 64: `audioSrc = /api/recordings/${recordingId}/audio` |
| `meeting-stat-cards.tsx` | `recording.ts` types | `Transcript` with `duration, processingTime` | WIRED | Props typed as `duration?: number`, `processingTime?: number` matching `Transcript` interface |
| `page.tsx` | `audio-player-bar.tsx` | rendered in detail page when status=ready | WIRED | Line 396: `<AudioPlayerBar recordingId={id} utterances={transcript?.utterances} />` |
| `audio-player-bar.tsx` | `audio-playback.ts` | `findActiveUtterance` + `setActiveUtterance` called on timeupdate | WIRED | Lines 102-110: `handleTimeUpdate` calls `findActiveUtterance` and `setActiveUtterance` |
| `transcript-view.tsx` | `audio-playback.ts` | reads `activeUtteranceIndex, autoScrollEnabled, isPlaying` | WIRED | Lines 21-27: all store selectors present; Resume follow + auto-scroll both wired |
| `utterance-bubble.tsx` | `audio-playback.ts` | `onSeek` calls `seek()` and `play()` (via TranscriptView) | WIRED | `transcript-view.tsx` line 30-36: `handleSeek` calls `seek(startTime)` then `play()`; passed as `onSeek` to each bubble |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DIAR-01 | 05-01 | Backend uses AgglomerativeClustering | SATISFIED | `transcription.py:16,147-153` |
| DIAR-02 | 05-01 | Speaker count auto-detected (no manual input) | SATISFIED | `n_clusters=None, distance_threshold=0.7` in `diarize()` |
| PLAY-01 | 05-03 | User can play/pause meeting audio | SATISFIED | `audio-player-bar.tsx` play/pause button wired to `togglePlayback()`; audio element syncs |
| PLAY-02 | 05-04 | Current utterance highlighted during playback | SATISFIED (automated checks pass) | `isPlaybackActive` prop triggers `bg-indigo-100/60`; `activeUtteranceIndex` updated on timeupdate | NEEDS HUMAN VERIFY |
| PLAY-03 | 05-03 | User can change playback speed (0.5x, 1x, 1.5x, 2x) | SATISFIED | `speed-selector.tsx` with 4 options; `audio.playbackRate` synced in `useEffect` |
| SPKR-03 | 05-01 | Per-speaker stats: time, words, WPM, turns, avg turn, pauses, avg pause | SATISFIED | `calculate_speaker_stats` computes all 7 metrics; displayed in `speaker-stats-panel.tsx` |
| SPKR-04 | 05-02 | Speakers color-coded in transcript view | SATISFIED | `speakerColors` palette applied via `getSpeakerIndex`; used in `UtteranceBubble` and `SpeakerBadge` |
| MEET-01 | 05-03 | User can view meeting duration | SATISFIED | `MeetingStatCards` displays `duration` from transcript; rendered above tabs in `page.tsx` |
| MEET-02 | 05-01, 05-03 | User can view processing time | SATISFIED | `processing_time` tracked in backend; passed through proxy; displayed in stat cards |
| MEET-03 | 05-03 | User can view number of speakers | SATISFIED | `speakerCount={transcript?.speakers?.length}` passed to `MeetingStatCards` |

**Note on REQUIREMENTS.md traceability:** PLAY-02 is marked `[ ]` (incomplete) and "Pending" in the REQUIREMENTS.md traceability table, despite being addressed by Plan 04. The checkbox and table entry should be updated to `[x]` / "Complete" to reflect the implementation. This is a documentation gap, not a code gap — the implementation exists.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

No TODOs, placeholders, empty implementations, or console.log-only handlers found in any phase 5 files.

### Human Verification Required

All 14 automated must-haves pass. The following behaviors require live runtime verification:

#### 1. Active Utterance Highlighting

**Test:** Open a ready recording. Click play. Watch the transcript.
**Expected:** The currently-playing utterance shows a soft indigo/blue background (bg-indigo-100/60) that updates every few seconds as playback advances.
**Why human:** Requires live `timeupdate` events from HTMLAudioElement; binary search result cannot be verified from static code alone.

#### 2. Auto-scroll with Manual Override

**Test:** Start playback. Manually scroll the transcript up. Observe. Click "Resume follow".
**Expected:** When you scroll manually during playback, a "Resume follow" button appears near the bottom. Auto-scroll stops. Clicking "Resume follow" causes the view to snap back to the active utterance and tracking resumes.
**Why human:** Requires real scroll events and DOM mutation to verify `isProgrammaticScroll` guard works correctly.

#### 3. Click-to-Seek

**Test:** Click any utterance bubble in the transcript.
**Expected:** Audio seeks to that utterance's start time and begins playing. The clicked utterance gets the indigo highlight.
**Why human:** Requires live audio element seek and confirmation audio plays from the correct position.

#### 4. Playback Speed

**Test:** During playback, open the speed dropdown and select 2x.
**Expected:** Audio plays noticeably faster. Dropdown shows "2x". Switching to 0.5x makes audio slower.
**Why human:** Requires live audio element and perceptual confirmation of speed change.

#### 5. Player Bar Layout

**Test:** Open a ready recording with the sidebar open and collapsed.
**Expected:** Player bar spans the content area width (not full viewport width, not cutting into sidebar). No content is hidden behind it (last utterance is accessible).
**Why human:** Portal-based layout with `#player-portal` inside `SidebarInset` requires visual inspection for correct width/positioning.

#### 6. Tab-switching Behavior

**Test:** Start audio playback, switch to Outcomes tab, then back to Transcript tab.
**Expected:** Player bar stays visible on all tabs. No highlighting appears on the Outcomes tab. Switching back to Transcript shows highlighting resume on the active utterance.
**Why human:** Requires live tab navigation with ongoing audio state.

### Gaps Summary

No gaps. All code artifacts exist, are substantive, and are wired end-to-end. The only outstanding items are live runtime behaviors that require human verification.

**Documentation note:** REQUIREMENTS.md marks PLAY-02 as `[ ]` (Pending) even though Plan 04 implements it. This should be updated to `[x]` (Complete) after human verification confirms the behavior works correctly.

---

_Verified: 2026-03-18T18:30:00Z_
_Verifier: Claude (gsd-verifier)_

