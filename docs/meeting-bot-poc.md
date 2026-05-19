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
RECORDING_MODE=audio    # 'both' also works -- watcher prefers .wav, falls
                        # back to -with-audio.mp4 if no .wav appears
AUDIO_FORMAT=wav
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
MEETING_BOT_URL=http://localhost:3001
MEETING_BOT_RECORDINGS_DIR=~/meeting-bot/recordings
FRONTEND_URL=http://localhost:3000

# Optional knobs
MEETING_BOT_POLL_SECONDS=2.0
MEETING_BOT_STABILITY_SECONDS=3.0
MEETING_BOT_MAX_MINUTES=185
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

## Known POC limitations

- **Mixed-stream mono audio.** The bot captures every remote participant in one channel via the meeting tab's audio output. SpeechBrain ECAPA-TDNN diarization with the current defaults (10 s window, cosine 0.7) may over- or under-cluster on heavily compressed voices. If the first end-to-end test shows poor speaker assignment, tune `FastDiarizer(window_size=..., distance_threshold=...)` in `backend/transcription.py:69`.
- **No completion webhook.** The simple bot doesn't notify when it finishes; the watcher polls (`size stable for 3s` + `/isbusy == 0`).
- **No bot-side auth.** Bind the bot to `127.0.0.1` only (default in `.env` above).
- **Bot must be running with `HEADLESS=false`.** Tab audio capture is unreliable in headless mode on macOS. The bot will open a visible Chrome window every time it joins.
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
