"""Environment-driven configuration for the meeting-bot integration."""

import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


MEETING_BOT_URL = _env("MEETING_BOT_URL", "http://localhost:3001").rstrip("/")
FRONTEND_URL = _env("FRONTEND_URL", "http://localhost:3000").rstrip("/")

MEETING_BOT_RECORDINGS_DIR = str(
    Path(_env("MEETING_BOT_RECORDINGS_DIR", "~/meeting-bot/recordings")).expanduser()
)

# How long to wait for the bot before declaring a dispatch failed. Matches the
# bot's MAX_RECORDING_DURATION_MINUTES default (180) plus a 5 min buffer.
MAX_RECORDING_MINUTES = int(_env("MEETING_BOT_MAX_MINUTES", "185"))

# Watcher tuning
WATCHER_POLL_SECONDS = float(_env("MEETING_BOT_POLL_SECONDS", "2.0"))
FILE_STABILITY_SECONDS = float(_env("MEETING_BOT_STABILITY_SECONDS", "3.0"))

# Forwarder transcode -- optional re-encode to a smaller 16 kHz mono MP3
# before uploading. DISABLED BY DEFAULT because the extra MP3 generation
# noticeably degrades Moonshine STT quality on the bot's already-compressed
# Meet audio (Meet Opus -> bot MP3 -> our MP3 -> backend PCM is three lossy
# stages, vs one for native browser recordings). Re-enable only if the
# upload size matters more than transcript accuracy.
FORWARD_TRANSCODE_ENABLED = _env("FORWARD_TRANSCODE_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
FORWARD_TRANSCODE_BITRATE = _env("FORWARD_TRANSCODE_BITRATE", "48k")
