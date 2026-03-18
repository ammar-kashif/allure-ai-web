# Phase 5: Diarization Upgrade & Audio Playback - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can play back meeting audio synced to the transcript with active line highlighting, and see enriched speaker and meeting statistics powered by improved AgglomerativeClustering diarization. Speaker editing (rename/roles) is Phase 6. Document attachments are Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Audio Player Design
- Sticky bottom bar on the recording detail page — always visible while scrolling, across all tabs (Info, Transcript, Outcomes, PRD, Diagram)
- Controls: play/pause toggle, draggable seek bar, current time / total time display, speed selector (0.5x, 1x, 1.5x, 2x)
- No skip forward/back buttons, no volume control
- Serve WAV files directly to the browser — backend already stores WAV, works everywhere including Safari, no conversion step needed

### Transcript-Audio Sync
- Active utterance highlighted with a distinct background color shift (soft indigo/blue tint) during playback
- Auto-scroll keeps active utterance visible; if user manually scrolls away, auto-scroll pauses and a "Resume follow" button appears to re-enable
- Clicking any utterance bubble seeks the player to that utterance's start time and starts playback
- Sync highlighting on Transcript tab only — no cross-tab sync with Outcomes

### Statistics Presentation
- Meeting stats (duration, processing time, speaker count) displayed as summary cards above the tab bar — always visible regardless of active tab
- Speaker stats (talk time, word count, WPM, turns, avg turn duration, pauses, avg pause duration) displayed in a collapsible panel at the top of the Transcript tab, above utterance bubbles
- All speaker stats always visible (no expand-to-reveal) — full breakdown shown for every speaker in the panel

### Speaker Color-Coding
- Consistent speaker colors everywhere: transcript bubbles, speaker stats panel, meeting stat cards
- Keep existing 5-color palette: indigo, teal, violet, amber, rose
- Speaker name shown as colored badge/pill (colored background) rather than plain text with dots
- Badges used in stats panel and transcript speaker labels

### Claude's Discretion
- Exact badge/pill styling (border radius, opacity, padding)
- Active utterance highlight color (suggested soft indigo/blue tint)
- "Resume follow" button placement and styling
- Meeting stat card layout and typography
- Collapsible panel animation and default state (open/closed)
- AgglomerativeClustering distance_threshold tuning approach
- Backend endpoint design for serving WAV audio files
- How processing time is tracked and returned from backend

</decisions>

<specifics>
## Specific Ideas

- Sticky player bar similar to Spotify's mini player — always accessible at the bottom
- Auto-scroll pauses on manual scroll (like YouTube live chat) with a resume button
- Click-to-seek on utterances makes the transcript a navigable timeline
- Speaker stats always fully visible — no hidden details behind expand toggles

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `utterance-bubble.tsx`: Has `speakerColors` array (indigo, teal, violet, amber, rose) with bg and label variants — extend to badges/pills
- `transcript-view.tsx`: Already has `highlightIndex` from evidence highlight store and scroll-to-highlight logic — adapt for playback sync
- `evidence-highlight.ts` (Zustand store): Manages activeTab and highlight state — can extend for audio playback state or create separate store
- `formatDuration` and `formatTimestamp` in `lib/utils` — reuse for player time display and meeting stats

### Established Patterns
- Tabs component from shadcn/ui used on recording detail page — add meeting stat cards above `<Tabs>`
- Zustand for cross-component state (evidence navigation) — follow same pattern for audio playback state
- TanStack Query for data fetching — use for fetching audio URL and extended transcript/stats data
- Backend returns `speakers` array with `talk_time_pct` and `utterance_count` — needs extension for WPM, word count, turns, avg turn, pauses, avg pause

### Integration Points
- Recording detail page (`recordings/[id]/page.tsx`): Add player bar component and meeting stat cards
- Transcript tab (`TranscriptView`): Add speaker stats panel above utterances, wire click-to-seek
- Backend `transcription.py`: Replace `MeanShift` with `AgglomerativeClustering`, extend `calculate_speaker_stats` for full SPKR-03 metrics
- Backend needs new endpoint to serve WAV audio file for browser playback
- Frontend `use-recordings.ts`: Extend to fetch audio URL and extended stats

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-diarization-upgrade-audio-playback*
*Context gathered: 2026-03-18*
