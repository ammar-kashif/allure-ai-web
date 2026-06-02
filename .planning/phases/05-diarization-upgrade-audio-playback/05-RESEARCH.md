# Phase 5: Diarization Upgrade & Audio Playback - Research

**Researched:** 2026-03-18
**Domain:** Audio playback (HTML5 Audio API), speaker diarization (sklearn AgglomerativeClustering), transcript-audio sync (Zustand state), meeting/speaker statistics
**Confidence:** HIGH

## Summary

This phase covers three interconnected workstreams: (1) upgrading the backend diarization from MeanShift to AgglomerativeClustering with auto-detected speaker count, (2) building a browser audio player with transcript sync, and (3) computing and displaying enriched speaker and meeting statistics.

The existing codebase provides strong foundations. The backend already stores WAV files at `backend/uploads/{job_id}.wav` and the frontend already has speaker color infrastructure in `utterance-bubble.tsx`, highlight/scroll logic in `transcript-view.tsx`, and Zustand state management patterns in `evidence-highlight.ts`. The primary work is: replacing MeanShift with AgglomerativeClustering in `transcription.py`, adding a WAV-serving endpoint, extending `calculate_speaker_stats` with word/WPM/turn/pause metrics, creating a Zustand audio playback store, building the sticky player bar component, adding click-to-seek and auto-scroll behavior, and adding stat display components.

**Primary recommendation:** Implement backend changes first (diarization upgrade + extended stats + audio endpoint), then build frontend audio player and stats display, then wire transcript sync last since it depends on both.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Audio player is a sticky bottom bar on the recording detail page -- always visible while scrolling, across all tabs
- Controls: play/pause toggle, draggable seek bar, current time / total time display, speed selector (0.5x, 1x, 1.5x, 2x)
- No skip forward/back buttons, no volume control
- Serve WAV files directly to the browser -- backend already stores WAV, works everywhere including Safari, no conversion step needed
- Active utterance highlighted with a distinct background color shift (soft indigo/blue tint) during playback
- Auto-scroll keeps active utterance visible; if user manually scrolls away, auto-scroll pauses and a "Resume follow" button appears to re-enable
- Clicking any utterance bubble seeks the player to that utterance's start time and starts playback
- Sync highlighting on Transcript tab only -- no cross-tab sync with Outcomes
- Meeting stats (duration, processing time, speaker count) displayed as summary cards above the tab bar -- always visible regardless of active tab
- Speaker stats (talk time, word count, WPM, turns, avg turn duration, pauses, avg pause duration) displayed in a collapsible panel at the top of the Transcript tab, above utterance bubbles
- All speaker stats always visible (no expand-to-reveal) -- full breakdown shown for every speaker in the panel
- Consistent speaker colors everywhere: transcript bubbles, speaker stats panel, meeting stat cards
- Keep existing 5-color palette: indigo, teal, violet, amber, rose
- Speaker name shown as colored badge/pill (colored background) rather than plain text with dots

### Claude's Discretion
- Exact badge/pill styling (border radius, opacity, padding)
- Active utterance highlight color (suggested soft indigo/blue tint)
- "Resume follow" button placement and styling
- Meeting stat card layout and typography
- Collapsible panel animation and default state (open/closed)
- AgglomerativeClustering distance_threshold tuning approach
- Backend endpoint design for serving WAV audio files
- How processing time is tracked and returned from backend

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DIAR-01 | Backend uses AgglomerativeClustering for speaker diarization | Replace MeanShift with AgglomerativeClustering in FastDiarizer.diarize(); sklearn 1.8.0 already installed |
| DIAR-02 | Speaker count is auto-detected (no manual input required) | Use distance_threshold parameter (no n_clusters) so AgglomerativeClustering auto-determines speaker count |
| PLAY-01 | User can play/pause meeting audio from the recording detail page | HTML5 Audio element + Zustand playback store + sticky bottom bar component |
| PLAY-02 | Current utterance is highlighted during audio playback | timeupdate event listener + binary search on utterance timestamps + highlight styling in utterance-bubble |
| PLAY-03 | User can change playback speed (0.5x, 1x, 1.5x, 2x) | HTMLAudioElement.playbackRate property |
| SPKR-03 | Per-speaker statistics (time, words, WPM, turns, avg turn, pauses, avg pause) | Extend calculate_speaker_stats in transcription.py to compute all metrics from segments |
| SPKR-04 | Speakers are color-coded in transcript view | Already partially done via speakerColors array; extend to badge/pill styling |
| MEET-01 | Meeting duration on recording detail page | Already returned as `duration` in TranscriptResponse; display as stat card |
| MEET-02 | Processing time on recording detail page | Track elapsed time in run_transcription; add processing_time to TranscriptResponse |
| MEET-03 | Number of speakers on recording detail page | Already derivable from `speakers` array length in TranscriptResponse |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.8.0 | AgglomerativeClustering for diarization | Already installed; drop-in replacement for MeanShift |
| Zustand | 5.0.11 | Audio playback state management | Project pattern for cross-component state (evidence-highlight store) |
| React (HTML5 Audio) | 19.2.3 | Audio playback in browser | Native HTMLAudioElement API; no library needed |
| shadcn/ui | 4.0.5 | UI components (Slider for seek bar, Collapsible for stats panel) | Project's component library |
| TanStack Query | 5.90.21 | Fetching audio URL and extended stats | Project's data fetching pattern |
| Tailwind CSS | 4.x | Styling player bar, stat cards, badges | Project's styling approach |

### Supporting (no new installs needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI | (backend) | Serve WAV audio files via FileResponse | New `/recordings/{id}/audio` endpoint |
| lucide-react | 0.577.0 | Player icons (Play, Pause, etc.) | Player controls UI |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTML5 Audio | howler.js / wavesurfer.js | Overkill -- no waveform viz needed, native Audio API is sufficient for play/pause/seek/speed |
| Zustand store for playback | React Context | Zustand already used for similar cross-component state; consistent pattern |

**Installation:**
No new npm or pip packages needed. All dependencies are already installed.

## Architecture Patterns

### Backend Changes

#### 1. AgglomerativeClustering Replacement
**File:** `backend/transcription.py` -- `FastDiarizer.diarize()`
**What:** Replace `MeanShift()` with `AgglomerativeClustering(n_clusters=None, distance_threshold=0.7, metric="cosine", linkage="average")`
**Why `distance_threshold`:** Setting `n_clusters=None` and providing `distance_threshold` enables auto-detection of speaker count (DIAR-02). The algorithm merges clusters until all inter-cluster distances exceed the threshold.

```python
# Source: sklearn 1.8.0 docs
from sklearn.cluster import AgglomerativeClustering

clustering = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=0.7,
    metric="cosine",
    linkage="average",
)
labels = clustering.fit_predict(embedding_matrix)
```

**Key difference from MeanShift:** MeanShift uses bandwidth estimation on Euclidean distance. AgglomerativeClustering with cosine metric is better for speaker embeddings because ECAPA-TDNN embeddings are L2-normalized, making cosine distance more discriminative than Euclidean.

#### 2. Extended Speaker Stats
**File:** `backend/transcription.py` -- `calculate_speaker_stats()`
**What:** Add word_count, wpm, turns, avg_turn_duration, pauses, avg_pause_duration per speaker.

```python
def calculate_speaker_stats(segments, total_duration):
    # For each speaker, compute:
    # - talk_time: sum of (end - start) for their segments
    # - talk_time_pct: percentage of total talk time
    # - word_count: sum of len(text.split()) for their segments
    # - utterance_count: number of segments (already exists)
    # - turns: same as utterance_count (each segment = one turn)
    # - avg_turn_duration: talk_time / turns
    # - wpm: word_count / (talk_time / 60)
    # - pauses: count of gaps between consecutive same-speaker segments
    # - avg_pause_duration: total pause time / pause count
```

#### 3. Processing Time Tracking
**File:** `backend/transcription.py` -- `run_transcription()`
**What:** Record `time.perf_counter()` at start and end, include `processing_time` in return dict.

#### 4. WAV Audio Serving Endpoint
**File:** `backend/main.py`
**What:** New `GET /recordings/{job_id}/audio` endpoint that returns the WAV file.

```python
from fastapi.responses import FileResponse

@app.get("/recordings/{job_id}/audio")
async def get_recording_audio(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    wav_path = job["file_path"]
    if not os.path.exists(wav_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        wav_path,
        media_type="audio/wav",
        headers={"Accept-Ranges": "bytes"},
    )
```

**Note:** FastAPI's `FileResponse` supports Range requests automatically via `starlette.responses.FileResponse`, which is critical for audio seeking in browsers. The `Accept-Ranges: bytes` header tells the browser that byte-range requests are supported.

#### 5. Next.js API Proxy for Audio
**File:** `src/app/api/recordings/[id]/audio/route.ts`
**What:** Proxy the WAV file from the backend to the frontend. Stream the response to avoid loading the full WAV into memory.

```typescript
export async function GET(request, { params }) {
    const { id } = await params
    const recording = getRecording(id)
    if (!recording?.backendId) return NextResponse.json({ error: "Not found" }, { status: 404 })

    const backendRes = await fetch(`${BACKEND_URL}/recordings/${recording.backendId}/audio`, {
        headers: request.headers.get("range")
            ? { Range: request.headers.get("range")! }
            : {},
    })

    return new Response(backendRes.body, {
        status: backendRes.status,
        headers: {
            "Content-Type": "audio/wav",
            "Accept-Ranges": "bytes",
            ...Object.fromEntries(
                ["content-length", "content-range"].filter(h => backendRes.headers.has(h))
                    .map(h => [h, backendRes.headers.get(h)!])
            ),
        },
    })
}
```

### Frontend Architecture

#### Audio Playback Store (Zustand)
**File:** `src/stores/audio-playback.ts`

```typescript
interface AudioPlaybackState {
  isPlaying: boolean
  currentTime: number       // seconds
  duration: number          // seconds
  playbackRate: number      // 0.5 | 1 | 1.5 | 2
  activeUtteranceIndex: number | null
  autoScrollEnabled: boolean
}

interface AudioPlaybackActions {
  play: () => void
  pause: () => void
  seek: (time: number) => void
  setPlaybackRate: (rate: number) => void
  setCurrentTime: (time: number) => void
  setDuration: (duration: number) => void
  setActiveUtterance: (index: number | null) => void
  disableAutoScroll: () => void
  enableAutoScroll: () => void
  reset: () => void
}
```

**Pattern:** Mirror the `evidence-highlight.ts` store pattern. The store holds playback state; the actual `HTMLAudioElement` is managed via a ref in the player component. Store actions dispatch to the audio element imperatively.

#### Sticky Player Bar Component
**File:** `src/components/audio/audio-player-bar.tsx`

- Renders as `fixed bottom-0` bar spanning full width of content area
- Contains: play/pause button, seek slider, time display, speed selector
- Manages `HTMLAudioElement` via `useRef`
- Syncs element events (timeupdate, loadedmetadata, ended) to Zustand store
- Only renders when recording status is "ready" and audio URL is available

#### Active Utterance Detection
**Pattern:** On each `timeupdate` event (~4Hz in browsers), binary search the utterances array to find which utterance contains `currentTime`.

```typescript
function findActiveUtterance(utterances: Utterance[], currentTime: number): number | null {
  // Binary search: utterances are sorted by startTime
  let low = 0, high = utterances.length - 1
  while (low <= high) {
    const mid = Math.floor((low + high) / 2)
    const u = utterances[mid]
    if (currentTime >= u.startTime && currentTime < u.endTime) return mid
    if (currentTime < u.startTime) high = mid - 1
    else low = mid + 1
  }
  return null
}
```

#### Auto-Scroll with Manual Override
**Pattern:** Track scroll position. When user scrolls manually (scroll event without programmatic trigger), set `autoScrollEnabled = false` and show "Resume follow" button. When clicked, re-enable and scroll to active utterance.

```typescript
// In TranscriptView:
const isManualScroll = useRef(false)
const isProgrammaticScroll = useRef(false)

// On scroll event:
if (!isProgrammaticScroll.current) {
  isManualScroll.current = true
  disableAutoScroll()
}

// On auto-scroll:
isProgrammaticScroll.current = true
element.scrollIntoView({ behavior: "smooth", block: "center" })
setTimeout(() => { isProgrammaticScroll.current = false }, 500)
```

### Recommended Component Structure
```
src/
  components/
    audio/
      audio-player-bar.tsx    # Sticky bottom player bar
      speed-selector.tsx      # Playback speed dropdown (0.5x/1x/1.5x/2x)
    transcript/
      transcript-view.tsx     # Extended with click-to-seek + auto-scroll
      utterance-bubble.tsx    # Extended with playback highlight + click handler
      speaker-stats-panel.tsx # Collapsible panel with per-speaker stats
      speaker-badge.tsx       # Colored badge/pill for speaker names
    recording/
      meeting-stat-cards.tsx  # Summary cards above tabs (duration, processing time, speakers)
  stores/
    audio-playback.ts         # Zustand store for playback state
  hooks/
    use-audio-playback.ts     # Hook wrapping store + audio element ref management (optional)
```

### Anti-Patterns to Avoid
- **Don't put Audio element in Zustand store:** Store holds state only; the HTMLAudioElement ref lives in the player component. Store actions call back to the element imperatively.
- **Don't poll for active utterance:** Use `timeupdate` event, not setInterval. The browser fires it at ~4Hz which is sufficient.
- **Don't re-render entire transcript on time update:** Only the active utterance index changes; use the index comparison in each bubble to avoid unnecessary re-renders.
- **Don't compute stats on frontend:** All speaker/meeting statistics should be computed on the backend and returned with the transcript response. Frontend just displays.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Seek bar / slider | Custom drag logic | shadcn/ui Slider component | Accessibility, keyboard nav, touch support built in |
| Audio streaming with range requests | Custom byte-range handling | FastAPI FileResponse | Starlette handles Range header parsing, partial content responses automatically |
| Collapsible panel | Custom show/hide toggle | shadcn/ui Collapsible component | Accessible, animated, keyboard support |
| Speaker color mapping | Duplicate color logic | Export `speakerColors` + `getSpeakerIndex` from utterance-bubble.tsx and share | Single source of truth for colors |
| Processing time formatting | Manual hour/min/sec math | Existing `formatDuration` from `lib/utils` | Already handles all cases |

**Key insight:** The existing codebase already has formatDuration, formatTimestamp, speaker color arrays, highlight/scroll logic, and Zustand patterns. Reuse aggressively.

## Common Pitfalls

### Pitfall 1: WAV File Size and Seeking
**What goes wrong:** WAV files are uncompressed and can be large (16kHz mono 16-bit = ~1.9 MB/minute). Browser may buffer slowly or fail to seek.
**Why it happens:** Without Range request support, the browser must download the entire file before seeking works.
**How to avoid:** FastAPI FileResponse already supports Range requests. Verify the proxy route (Next.js API) also forwards the Range header correctly. Test seeking to the middle of a 10+ minute recording.
**Warning signs:** Seek bar jumps back to 0, or seeking to later timestamps causes a long pause.

### Pitfall 2: timeupdate Frequency and Highlight Flicker
**What goes wrong:** The `timeupdate` event fires at irregular intervals (~250ms but not guaranteed). If utterances are very short, the highlight might skip or flicker.
**Why it happens:** Browser doesn't guarantee exact timing for timeupdate.
**How to avoid:** Use >= comparison (not exact match) in the active utterance finder. If currentTime is between two utterances (gap), keep the previous utterance highlighted rather than setting null.
**Warning signs:** Highlight flashing on/off between utterances.

### Pitfall 3: AgglomerativeClustering distance_threshold Sensitivity
**What goes wrong:** Threshold too low = over-segmentation (too many speakers). Too high = under-segmentation (everyone is one speaker).
**Why it happens:** ECAPA-TDNN cosine distances vary with audio quality, number of speakers, and recording conditions.
**How to avoid:** Start with distance_threshold=0.7. Test on 3-5 real recordings with known speaker counts. Adjust if needed. Document the tuning in comments.
**Warning signs:** Consistently wrong speaker counts across recordings.

### Pitfall 4: Auto-Scroll Fighting User Scroll
**What goes wrong:** User tries to read ahead/behind in transcript but auto-scroll keeps yanking them back.
**Why it happens:** timeupdate fires frequently and triggers scrollIntoView.
**How to avoid:** Implement manual-scroll detection. When user scrolls, disable auto-scroll and show "Resume follow" button. Only programmatic scrolls set a flag to differentiate.
**Warning signs:** Users can't read other parts of the transcript during playback.

### Pitfall 5: Backend SpeakerStats Model Mismatch
**What goes wrong:** Adding new fields to the backend `SpeakerStats` Pydantic model but the frontend transcript API proxy doesn't pass them through.
**Why it happens:** The transcript API route (`src/app/api/recordings/[id]/transcript/route.ts`) transforms backend data -- currently only maps segments, not speakers. The speaker stats are dropped.
**How to avoid:** Update the transcript route to also pass through the full `speakers` array (with new fields) and `duration` and `processing_time`. Update the `Transcript` TypeScript type to include speakers and meeting-level stats.
**Warning signs:** Stats panel shows no data or undefined values.

### Pitfall 6: Sticky Player Bar Overlapping Content
**What goes wrong:** The fixed-position player bar covers the bottom of page content, including the last few transcript utterances.
**Why it happens:** Fixed positioning removes the element from document flow.
**How to avoid:** Add padding-bottom to the recording detail page container equal to the player bar height (e.g., `pb-20`). Only apply when player is visible.
**Warning signs:** Last transcript utterance hidden behind player bar.

## Code Examples

### AgglomerativeClustering Drop-In Replacement
```python
# In FastDiarizer.diarize(), replace MeanShift block:
# OLD:
# clustering = MeanShift()
# labels = clustering.fit_predict(embedding_matrix)

# NEW:
from sklearn.cluster import AgglomerativeClustering

clustering = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=0.7,
    metric="cosine",
    linkage="average",
)
labels = clustering.fit_predict(embedding_matrix)
```
**Confidence:** HIGH -- sklearn 1.8.0 is installed, AgglomerativeClustering API is stable since sklearn 0.22.

### Extended SpeakerStats
```python
# Backend model extension
class SpeakerStats(BaseModel):
    label: str
    talk_time_pct: float
    utterance_count: int
    talk_time: float          # seconds
    word_count: int
    wpm: float                # words per minute
    turns: int                # same as utterance_count
    avg_turn_duration: float  # seconds
    pauses: int               # gaps between consecutive turns
    avg_pause_duration: float # seconds, 0.0 if no pauses
```

### HTMLAudioElement Playback Rate
```typescript
// Source: MDN Web API
const audioRef = useRef<HTMLAudioElement>(null)

// Set speed:
if (audioRef.current) {
  audioRef.current.playbackRate = 1.5  // 0.5 | 1 | 1.5 | 2
}

// Listen for time updates:
audioRef.current.addEventListener("timeupdate", () => {
  const time = audioRef.current!.currentTime
  setCurrentTime(time)
  setActiveUtterance(findActiveUtterance(utterances, time))
})
```
**Confidence:** HIGH -- standard Web API, supported in all modern browsers.

### Speaker Badge Component
```typescript
// Reuse existing color palette from utterance-bubble.tsx
const speakerColors = [
  { bg: "bg-indigo-100", label: "text-indigo-700", border: "border-indigo-200" },
  { bg: "bg-teal-100", label: "text-teal-700", border: "border-teal-200" },
  { bg: "bg-violet-100", label: "text-violet-700", border: "border-violet-200" },
  { bg: "bg-amber-100", label: "text-amber-700", border: "border-amber-200" },
  { bg: "bg-rose-100", label: "text-rose-700", border: "border-rose-200" },
]

function SpeakerBadge({ speaker }: { speaker: string }) {
  const colorIndex = getSpeakerIndex(speaker)
  const colors = speakerColors[colorIndex]
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", colors.bg, colors.label)}>
      {speaker}
    </span>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MeanShift (bandwidth auto) | AgglomerativeClustering (distance_threshold) | This phase | Better cosine metric support for speaker embeddings; more predictable speaker count |
| No audio playback | HTML5 Audio with sticky player bar | This phase | Users can listen to recordings |
| Basic speaker stats (pct, count) | Full stats (WPM, turns, pauses, etc.) | This phase | Richer meeting analytics |

## Open Questions

1. **AgglomerativeClustering distance_threshold value**
   - What we know: 0.7 is a common starting point for ECAPA-TDNN cosine distances
   - What's unclear: Optimal value depends on recording conditions (microphone, room, number of speakers)
   - Recommendation: Start with 0.7, test on 3-5 recordings, adjust. Add a comment documenting the choice.

2. **Processing time -- what to include?**
   - What we know: Total pipeline time (STT + diarization + alignment + stats)
   - What's unclear: Should it include queue wait time or just processing time?
   - Recommendation: Track only active processing time (from when `run_transcription` starts to when it returns). Queue wait time is infrastructure, not useful to users.

3. **Large WAV file streaming performance**
   - What we know: WAV at 16kHz mono 16-bit is ~1.9 MB/min. A 30-min meeting = ~57 MB.
   - What's unclear: Whether the Next.js proxy adds latency for seeking in large files.
   - Recommendation: Implement and test. If proxy is too slow, consider serving audio directly from backend URL (CORS already configured). But try proxy first for consistency.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | Vitest 4.0.18 + Testing Library |
| Framework (backend) | pytest |
| Config file (frontend) | `vitest.config.ts` |
| Config file (backend) | `backend/tests/` directory |
| Quick run command (frontend) | `npx vitest run --reporter=verbose` |
| Quick run command (backend) | `cd backend && .venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `npx vitest run && cd backend && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DIAR-01 | AgglomerativeClustering used for diarization | unit | `cd backend && .venv/bin/python -m pytest tests/test_transcription.py -x -k agglomerative` | No -- Wave 0 |
| DIAR-02 | Speaker count auto-detected | unit | `cd backend && .venv/bin/python -m pytest tests/test_transcription.py -x -k auto_speakers` | No -- Wave 0 |
| PLAY-01 | Play/pause audio | integration | `npx vitest run src/components/audio/__tests__/audio-player-bar.test.tsx` | No -- Wave 0 |
| PLAY-02 | Active utterance highlighted | unit | `npx vitest run src/components/transcript/__tests__/transcript-view.test.tsx -t "highlight"` | Partial (exists but needs playback highlight tests) |
| PLAY-03 | Playback speed change | unit | `npx vitest run src/components/audio/__tests__/audio-player-bar.test.tsx -t "speed"` | No -- Wave 0 |
| SPKR-03 | Per-speaker extended stats | unit | `cd backend && .venv/bin/python -m pytest tests/test_transcription.py -x -k extended_stats` | No -- Wave 0 |
| SPKR-04 | Speaker color-coding | unit | `npx vitest run src/components/transcript/__tests__/utterance-bubble.test.tsx` | Yes (existing) |
| MEET-01 | Meeting duration display | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx` | No -- Wave 0 |
| MEET-02 | Processing time display | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx -t "processing"` | No -- Wave 0 |
| MEET-03 | Speaker count display | unit | `npx vitest run src/components/recording/__tests__/meeting-stat-cards.test.tsx -t "speakers"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run --reporter=verbose` (frontend) or `cd backend && .venv/bin/python -m pytest tests/ -x -q` (backend)
- **Per wave merge:** Full suite: both frontend and backend tests
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_transcription.py` -- add tests for AgglomerativeClustering (DIAR-01, DIAR-02) and extended speaker stats (SPKR-03)
- [ ] `src/components/audio/__tests__/audio-player-bar.test.tsx` -- covers PLAY-01, PLAY-03
- [ ] `src/components/recording/__tests__/meeting-stat-cards.test.tsx` -- covers MEET-01, MEET-02, MEET-03
- [ ] `src/components/transcript/__tests__/transcript-view.test.tsx` -- extend for playback highlight tests (PLAY-02)

## Sources

### Primary (HIGH confidence)
- Project codebase: `backend/transcription.py` (current MeanShift implementation, calculate_speaker_stats)
- Project codebase: `backend/main.py` (FastAPI endpoints, FileResponse pattern)
- Project codebase: `src/components/transcript/utterance-bubble.tsx` (speakerColors, getSpeakerIndex)
- Project codebase: `src/stores/evidence-highlight.ts` (Zustand store pattern)
- Project codebase: `src/app/api/recordings/[id]/transcript/route.ts` (backend proxy pattern)
- sklearn 1.8.0 installed in backend venv (AgglomerativeClustering API)

### Secondary (MEDIUM confidence)
- MDN Web API documentation for HTMLAudioElement (playbackRate, timeupdate, seeking)
- FastAPI FileResponse for static file serving with Range requests

### Tertiary (LOW confidence)
- AgglomerativeClustering distance_threshold=0.7 as starting value for ECAPA-TDNN embeddings (needs empirical validation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed, no new dependencies
- Architecture: HIGH -- clear patterns from existing codebase (Zustand stores, API proxies, component structure)
- Pitfalls: HIGH -- identified from codebase analysis (proxy forwarding, scroll conflicts, model mismatches)
- Diarization tuning: LOW -- distance_threshold value needs empirical testing

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable domain, no fast-moving dependencies)

