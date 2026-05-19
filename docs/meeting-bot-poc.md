# Live meetings via the meeting bot — POC operator guide

This is the single-machine POC for piping a real Google Meet / Microsoft Teams / Zoom call through Allure's existing transcription + extraction pipeline. A Puppeteer-based bot joins the meeting, records the audio, and a watcher inside Allure's backend hands the file off to the regular upload flow with no human upload step.

## Architecture summary

```
CLI (dispatch) ──► POST /meetings/dispatch ──► bot /<platform>/join
                            │                          │
                            │                          ▼
                            │                  recordings/<rec_id>/*.wav
                            │                          │
                            ▼                          ▼
                  dispatch_store (SQLite) ◄── watcher polling
                                                       │
                                                       ▼
                                       POST /api/recordings (frontend)
                                                       │
                                                       ▼
                                       STT → diarize → outcomes (existing)
```

The bot writes files to `<LOCAL_RECORDINGS_DIR>/<userId>/...`. Because the dispatch endpoint passes `userId = recording_id`, every meeting lands in a unique directory the watcher can map back to a row in the `dispatches` table.

## One-time setup

### 1. Clone and install the bot

```bash
cd ~
git clone https://github.com/moawizbinyamin/meeting-bot
cd meeting-bot
npm install
```

Make sure `node --version` is 20+ and `ffmpeg -version` works (the bot shells out to ffmpeg).

### 2. Bot environment

Create `~/meeting-bot/.env`:

```bash
# Run on a different port -- Allure's frontend is on :3000
PORT=3001

# Bind to localhost only -- the bot has no auth in simple mode
HOST=127.0.0.1

SIMPLE_BOT=true
HEADLESS=false          # required for reliable tab audio
UPLOADER_TYPE=local
RECORDING_MODE=audio    # audio-only; 'both' also works but adds a video file
AUDIO_FORMAT=mp3        # ~8x smaller than WAV. See "Size budget" below.
LOCAL_RECORDINGS_DIR=/Users/<you>/meeting-bot/recordings
GOOGLE_GUEST_MODE=true  # or false if you've run `npm run google:login`
DISABLE_CAMERA=true
USE_REAL_MICROPHONE=false
JOIN_WAIT_TIME_MINUTES=10
```

Whatever you set for `LOCAL_RECORDINGS_DIR` must match Allure's `MEETING_BOT_RECORDINGS_DIR` (see below).

### 3. Allure environment

Add to your Allure root `.env` (used by `backend`):

```bash
# REQUIRED on macOS to avoid the Phi-4 + Moonshine OpenMP deadlock -- see
# "Known POC limitations" below.
LLM_GPU=1

MEETING_BOT_URL=http://localhost:3001
MEETING_BOT_RECORDINGS_DIR=~/meeting-bot/recordings
FRONTEND_URL=http://localhost:3000

# Optional knobs
MEETING_BOT_POLL_SECONDS=2.0
MEETING_BOT_STABILITY_SECONDS=3.0
MEETING_BOT_MAX_MINUTES=185

# Forwarder transcode (defaults shown). Resamples each recording to 16 kHz
# mono MP3 before uploading to the frontend -- cuts upload size ~4-5x on
# top of the bot's MP3 output. Set FORWARD_TRANSCODE_ENABLED=false to
# upload the raw source.
FORWARD_TRANSCODE_ENABLED=true
FORWARD_TRANSCODE_BITRATE=48k
```

## Running the POC

In three terminals:

```bash
# 1. Start the bot
cd ~/meeting-bot && npm start

# 2. Start Allure (Docker)
cd ~/allure-ai-web && docker-compose up

# 3. Dispatch a meeting
cd ~/allure-ai-web/backend
.venv/bin/python -m meeting_bot.cli dispatch \
    --url "https://meet.google.com/abc-defg-hij" \
    --title "POC test"
```

The CLI prints `{recording_id, status, platform, bot_response}`. Save that `recording_id` — you can poll its progress with:

```bash
.venv/bin/python -m meeting_bot.cli status <recording_id>
```

## What happens

1. **`POST /meetings/dispatch`** generates `recording_id`, inserts a row in `dispatches` (status `dispatched`), and sends `POST /google/join` to the bot with `userId = recording_id` so the bot writes to `recordings/<recording_id>/...`.
2. **Bot joins the meeting.** You will see a tab open in Chrome. Approve the bot into the meeting from the host UI.
3. **Recording.** The bot captures the meeting tab's audio into `recordings/<recording_id>/Google Meet - Allure-XXXXXXXX - <iso>.wav`.
4. **Watcher.** Every 2 s, the watcher checks pending dispatches. The first time it sees the `.wav`, it flips `status` to `recording`. Once the file size is stable for 3 s **and** `GET /isbusy` returns 0 **and** there are no `.tmp.*` siblings, it flips to `forwarding`.
5. **Forward.** The watcher POSTs the file as multipart to `http://localhost:3000/api/recordings` with `recordingId`, `title`, `durationMs`, optional `projectId`. The frontend creates the user-facing recording row and proxies it to the backend's existing `POST /recordings`.
6. **Existing pipeline.** STT (Moonshine) → speaker diarization (SpeechBrain) → outcome extraction (Phi-4-mini). Same code path as a browser-uploaded recording.
7. **`status` flips to `ingested`.** The recording shows up in the Allure dashboard.

## Verifying

| Stage | How to check |
|---|---|
| Dispatch row created | `python -m meeting_bot.cli status <rec_id>` shows `status: dispatched` |
| File on disk | `ls ~/meeting-bot/recordings/<rec_id>/` shows a `.wav` |
| File handed off | `status` flips through `recording → forwarding → ingested` |
| Transcript exists | `curl localhost:8000/recordings/<rec_id>/transcript` returns segments |
| Outcomes extracted | `curl localhost:8000/recordings/<rec_id>/outcomes` returns a list |
| UI surfaces it | Open `http://localhost:3000/recordings` — the title appears |

## Size budget

A 3-minute Google Meet recording, end-to-end:

| Stage | Bot `wav` only | + bot `mp3` | + forwarder transcode (default) |
|---|---|---|---|
| Bot writes to disk | ~25 MB (44.1k stereo PCM) | ~3 MB (mp3 VBR q=2) | ~3 MB (unchanged at bot) |
| Network: bot watcher → frontend → backend | 25 MB × 2 hops | 3 MB × 2 hops | **~800 KB × 2 hops** |
| Backend canonical WAV (`backend/uploads/<id>.wav`) | 4.6 MB (16k mono PCM) | 4.6 MB | 4.6 MB (unchanged — backend always normalizes) |

Two independent knobs:

1. **Bot `AUDIO_FORMAT=mp3`** (operator-side, in `~/meeting-bot/.env`). Cuts what the bot writes to disk ~8×. Watcher (`backend/meeting_bot/watcher.py:_AUDIO_EXTENSIONS`) prefers `.mp3` first, so no Allure code change needed.
2. **`FORWARD_TRANSCODE_ENABLED=true`** (Allure-side, default on). The forwarder runs `ffmpeg -ar 16000 -ac 1 -c:a libmp3lame -b:a 48k` on each recording before POSTing to the frontend. The backend always downsamples to 16 kHz mono anyway, so this just cuts what crosses the wire. On ffmpeg failure the forwarder falls back to uploading the raw source — one bad file can't sink the pipeline. Tunable via `FORWARD_TRANSCODE_BITRATE` (default `48k`, override to `32k` for even smaller files or `64k` for headroom).

Net effect with both enabled: a 25 MB raw-WAV pipeline becomes an ~800 KB upload — ~30× reduction with no measurable hit to Moonshine STT or speaker stats.

## Known POC limitations

- **Run the backend with `LLM_GPU=1` (Metal) on macOS — mandatory.** Phi-4-mini via llama-cpp on pure CPU (`LLM_GPU=0`) grabs the global OpenMP thread pool and deadlocks Moonshine's OpenMP-based inference. STT hangs forever, the worker thread sits at 0 % CPU, no error is logged. Verified on Apple Silicon: with `LLM_GPU=1` the pipeline completes in <60 s; with `LLM_GPU=0` it never returns. If you must run pure-CPU, you'll need to pin one of the two libs to a single thread (`OMP_NUM_THREADS=1`) before importing it, but that defeats the parallelism.
- **Mixed-stream mono audio.** The bot captures every remote participant in one channel via the meeting tab's audio output. SpeechBrain ECAPA-TDNN diarization with the current defaults (10 s window, cosine 0.7) often collapses multiple speakers into one on short or heavily compressed samples (we saw 2 voices merge into 1 on a 2.4 min POC recording). Tune `FastDiarizer(window_size=..., distance_threshold=...)` in `backend/transcription.py:69` if assignment is poor — drop `distance_threshold` to 0.5 first, then `window_size` to 4 s.
- **Bot dropped into a Workspace-restricted Meet?** Guest mode (`GOOGLE_GUEST_MODE=true`) is rejected by Google Workspace tenants that disallow unauthenticated participants. Run `npm run google:login` once (interactive Chrome popup) to save a signed-in profile to `~/meeting-bot/.puppeteer-profile`, then set `GOOGLE_GUEST_MODE=false`.
- **macOS Chrome path.** `npm install` downloads Chrome for Testing to `~/.cache/puppeteer/chrome/mac_arm-<version>/...`. Set `CHROME_PATH=<that path>/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing` in the bot's `.env`. The bot's default `/usr/bin/google-chrome` is Linux-only.
- **No completion webhook.** The simple bot doesn't notify when it finishes; the watcher polls (`size stable for 3s` + `/isbusy == 0`).
- **No bot-side auth.** Bind the bot to `127.0.0.1` only (default in `.env` above).
- **Headless vs visible.** `HEADLESS=true` works on macOS for Meet audio capture in our testing and avoids a Dock icon entirely. If audio quality drops in your environment, flip to `HEADLESS=false` and put the visible Chrome window on a different Space.
- **Recording cap.** The bot's own `MAX_RECORDING_DURATION_MINUTES` defaults to 180. Allure's `MEETING_BOT_MAX_MINUTES` (185) is the absolute fail-fast for a crashed bot.

## Failure modes and recovery

| Symptom | What happened | Fix |
|---|---|---|
| Dispatch returns 502 | Bot service is down or misconfigured | Check `~/meeting-bot/npm start` output |
| Dispatch returns 400 with "infer platform" | URL host wasn't recognized | Pass `--platform` explicitly |
| `status` stays `dispatched` indefinitely | Bot didn't get into the meeting (waiting room not approved, captcha) | Watch the Chrome window the bot opened |
| `status` stuck at `recording` | File is growing but never stabilizes | Check ffmpeg sub-process in the bot logs |
| `status: failed`, error mentions "bot timeout" | Dispatch older than `MEETING_BOT_MAX_MINUTES` | Bot crashed; check bot logs and re-dispatch |
| `status: failed`, error mentions HTTP 4xx | Frontend rejected the upload | Check `frontend` logs for the validation failure |

## Where the code lives

- `backend/meeting_bot/router.py` — `POST /meetings/dispatch`, `GET /meetings/{id}`
- `backend/meeting_bot/bot_client.py` — HTTP client for the bot
- `backend/meeting_bot/dispatch_store.py` — SQLite CRUD for the `dispatches` table
- `backend/meeting_bot/watcher.py` — the polling loop, wired into the FastAPI lifespan in `backend/main.py`
- `backend/meeting_bot/forwarder.py` — multipart upload to the frontend
- `backend/meeting_bot/cli.py` — the `dispatch` and `status` subcommands
