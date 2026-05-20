# Bot patch — streaming chunk output

Adds a parallel ffmpeg segment output to the bot so Allure can process the
recording chunk-by-chunk while the meeting is still running. The existing
whole-file output is unchanged (backward compatibility + fallback).

## What changes in the bot

Wherever the bot launches ffmpeg to encode the recording (typically in
`GoogleMeetSimpleBot.ts` → `screenRecorder.ts` or `audioCapture.ts`), add
a second output pad after the existing one:

```bash
ffmpeg -y \
  -i <input> \
  # ── existing whole-file output (unchanged) ──
  -map 0 -c:a libmp3lame -b:a 96k <recordings_dir>/<recording_id>/recording.mp3 \
  # ── new parallel segment output ──
  -map 0 -reset_timestamps 1 \
  -f segment -segment_time 30 \
  -segment_format mp3 -c:a libmp3lame -b:a 96k \
  <recordings_dir>/<recording_id>/chunks/%06d.mp3
```

Key flags:
- `-segment_time 30` → 30-second chunks. Tune via env var if needed.
- `-reset_timestamps 1` → each chunk starts from 0:00 locally; Allure's
  chunk worker translates back to meeting-global time using the seq number.
- `%06d.mp3` → monotonic zero-padded sequence (`000001.mp3`, `000002.mp3`,
  ...). The Allure watcher picks them up in order.

## Filesystem layout the backend expects

```
<recordings_dir>/
  <recording_id>/
    recording.mp3                 ← existing whole-file output
    chunks/
      000001.mp3                  ← appears at ~T+30s
      000002.mp3                  ← appears at ~T+60s
      ...
```

## Backend integration

Allure's existing watcher (`meeting_bot/watcher.py`) already polls each
in-flight dispatch on a 2s loop. The streaming-chunk discovery hook runs
inside that same loop:

1. On every tick, the watcher checks `chunks/` under the recording id.
2. Any file `NNNNNN.{mp3,wav}` not already in `chunk_progress` is upserted
   and enqueued onto the chunk queue.
3. The highest-numbered file is **excluded** until the next tick because
   ffmpeg may still be writing it.
4. Chunk workers (configurable pool, default 2) process each chunk:
   STT + VAD + embedding extraction. Results land in `chunk_progress`.
5. When the watcher's existing whole-file logic detects the bot is idle
   and finalized, the streaming finalize is enqueued — it pools all chunk
   embeddings, runs global speaker clustering, and produces the canonical
   transcript that extraction then runs against.

## If you don't apply this patch

Nothing breaks. Without the `chunks/` directory the watcher's chunk
discovery is a no-op and the existing whole-file path runs unchanged.
You just don't get streaming-pipeline latency wins.

## Verifying

```bash
# while a meeting is recording
ls -1 ~/meeting-bot/recordings/<recording_id>/chunks/
# 000001.mp3   ← appears at +30s
# 000002.mp3   ← appears at +60s

curl http://localhost:8000/logs?category=streaming
# step.done events: streaming.chunk_stt, streaming.chunk_embeddings,
# chunk.done one per chunk
```

A live transcript stream is also available at:
```
GET /recordings/<recording_id>/transcript/stream
```
as Server-Sent Events; each `chunk` event carries that chunk's STT
segments with `speaker: "pending"` (final speakers are backfilled by the
post-meeting finalize step).
