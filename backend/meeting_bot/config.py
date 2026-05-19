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

# Forwarder transcode -- normalize each recording to 16 kHz mono MP3 before
# uploading to the frontend. Allure only ever consumes 16 kHz mono, so this
# cuts upload size by ~4-5x on top of the bot's MP3 output (~30x vs raw WAV).
FORWARD_TRANSCODE_ENABLED = _env("FORWARD_TRANSCODE_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
FORWARD_TRANSCODE_BITRATE = _env("FORWARD_TRANSCODE_BITRATE", "48k")
