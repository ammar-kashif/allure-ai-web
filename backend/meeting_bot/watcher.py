"""Filesystem watcher that bridges finished bot recordings into Allure.

Lifecycle (per dispatch row, polled every WATCHER_POLL_SECONDS):

    dispatched -> recording -> forwarding -> ingested|failed

The watcher only acts when ALL of the following hold:
    1. `<recordings_dir>/<recording_id>/` exists and contains a .wav (or, as a
       fallback, a `-with-audio.mp4`).
    2. The chosen file has the same (size, mtime) as last poll AND was last
       modified > FILE_STABILITY_SECONDS ago.
    3. The bot's `/isbusy` returns 0.
    4. No `.tmp.webm` sibling -- ffmpeg is still finalizing.

This belt-and-suspenders approach is necessary because the simple bot
writes ffmpeg output directly (no temp+rename) and exposes no completion
webhook.

A timeout (config.MAX_RECORDING_MINUTES) fails dispatches that have been
waiting too long, so a crashed bot can't pin a row forever.
"""

import asyncio
import datetime as dt
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from meeting_bot import dispatch_store
from meeting_bot.bot_client import BotClient
from meeting_bot.config import (
    FILE_STABILITY_SECONDS,
    MAX_RECORDING_MINUTES,
    MEETING_BOT_RECORDINGS_DIR,
    WATCHER_POLL_SECONDS,
)
from meeting_bot.forwarder import ForwardError, forward_to_frontend

logger = logging.getLogger(__name__)

# Order matters: prefer the muxed audio file the bot finalizes last.
_AUDIO_EXTENSIONS = (".wav", "-with-audio.mp4", ".mp3")


@dataclass
class _FileSnapshot:
    path: str
    size: int
    mtime: float


def _find_candidate_audio(directory: str) -> Optional[str]:
    """Return the newest finalized audio file in `directory`, or None.

    Skips `.tmp.*` siblings (ffmpeg's in-progress output).
    """
    if not os.path.isdir(directory):
        return None

    candidates: list[tuple[float, str]] = []
    for name in os.listdir(directory):
        if name.startswith(".") or ".tmp." in name:
            continue
        if not any(name.endswith(ext) for ext in _AUDIO_EXTENSIONS):
            continue
        full = os.path.join(directory, name)
        try:
            stat = os.stat(full)
        except OSError:
            continue
        candidates.append((stat.st_mtime, full))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _has_tmp_sibling(directory: str) -> bool:
    if not os.path.isdir(directory):
        return False
    return any(".tmp." in name for name in os.listdir(directory))


def _snapshot(path: str) -> Optional[_FileSnapshot]:
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return _FileSnapshot(path=path, size=stat.st_size, mtime=stat.st_mtime)


def _is_stable(snap: _FileSnapshot, now: float) -> bool:
    """True if the file has not been touched within the stability window."""
    return (now - snap.mtime) >= FILE_STABILITY_SECONDS


async def _handle_dispatch(
    row: dict,
    *,
    bot: BotClient,
    last_snapshots: dict[str, _FileSnapshot],
    recordings_dir: str,
    forward_fn,
) -> None:
    rec_id = row["recording_id"]
    rec_dir = os.path.join(recordings_dir, rec_id)

    # Timeout: a dispatch sitting around > MAX_RECORDING_MINUTES + a few mins
    # has almost certainly seen a bot crash. Fail it loudly.
    dispatched_at = dt.datetime.fromisoformat(row["dispatched_at"])
    age_minutes = (dt.datetime.utcnow() - dispatched_at).total_seconds() / 60
    if age_minutes > MAX_RECORDING_MINUTES:
        logger.warning("Dispatch %s timed out after %.1f min", rec_id, age_minutes)
        dispatch_store.update(
            rec_id,
            status="failed",
            error=f"bot timeout after {int(age_minutes)} min",
            finalized_at=dt.datetime.utcnow().isoformat(timespec="seconds"),
        )
        last_snapshots.pop(rec_id, None)
        return

    candidate = _find_candidate_audio(rec_dir)
    if candidate is None:
        return  # bot hasn't produced anything yet

    # Move row to 'recording' the first time we see a file.
    if row["status"] == "dispatched":
        dispatch_store.update(rec_id, status="recording", audio_path=candidate)

    snap = _snapshot(candidate)
    if snap is None:
        return

    now = time.time()
    prev = last_snapshots.get(rec_id)
    last_snapshots[rec_id] = snap

    # Need at least two observations and a stable (size, mtime) window.
    if prev is None or prev.path != snap.path or prev.size != snap.size:
        return
    if not _is_stable(snap, now):
        return

    if _has_tmp_sibling(rec_dir):
        return

    if await bot.is_busy():
        return

    # All conditions met -> forward to the frontend.
    dispatch_store.update(rec_id, status="forwarding", audio_path=snap.path)
    title = row.get("title") or f"Meeting {rec_id[:8]}"
    project_id = row.get("project_id")

    try:
        await forward_fn(
            audio_path=snap.path,
            recording_id=rec_id,
            title=title,
            project_id=project_id,
        )
    except ForwardError as exc:
        logger.error("Forward failed for %s: %s", rec_id, exc)
        dispatch_store.update(
            rec_id,
            status="failed",
            error=str(exc),
            finalized_at=dt.datetime.utcnow().isoformat(timespec="seconds"),
        )
        last_snapshots.pop(rec_id, None)
        return

    dispatch_store.update(
        rec_id,
        status="ingested",
        finalized_at=dt.datetime.utcnow().isoformat(timespec="seconds"),
    )
    last_snapshots.pop(rec_id, None)
    logger.info("Recording %s ingested into Allure", rec_id)


async def _watch_loop(
    *,
    bot: BotClient,
    recordings_dir: str,
    poll_seconds: float,
    forward_fn,
    stop_event: asyncio.Event,
) -> None:
    """Single pass over pending dispatches, repeated until stop_event is set."""
    snapshots: dict[str, _FileSnapshot] = {}
    while not stop_event.is_set():
        try:
            pending = dispatch_store.list_pending()
        except Exception as exc:
            logger.error("dispatch_store.list_pending failed: %s", exc)
            pending = []

        for row in pending:
            try:
                await _handle_dispatch(
                    row,
                    bot=bot,
                    last_snapshots=snapshots,
                    recordings_dir=recordings_dir,
                    forward_fn=forward_fn,
                )
            except Exception as exc:  # noqa: BLE001 - never let one row sink the loop
                logger.exception(
                    "Watcher tick failed for %s: %s", row.get("recording_id"), exc
                )

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
        except asyncio.TimeoutError:
            pass


def run_watcher(app_state) -> asyncio.Task:
    """Launch the watcher as an asyncio task. Stored on app_state for shutdown.

    The bot client is shared with the dispatch router (`router._bot_client`)
    so an env-driven override there is honored here too.
    """
    from meeting_bot.router import get_bot_client

    bot = get_bot_client()
    stop_event = asyncio.Event()
    app_state.bot_watcher_stop = stop_event

    async def _runner():
        os.makedirs(MEETING_BOT_RECORDINGS_DIR, exist_ok=True)
        logger.info(
            "meeting-bot watcher started (dir=%s, poll=%.1fs)",
            MEETING_BOT_RECORDINGS_DIR,
            WATCHER_POLL_SECONDS,
        )
        await _watch_loop(
            bot=bot,
            recordings_dir=MEETING_BOT_RECORDINGS_DIR,
            poll_seconds=WATCHER_POLL_SECONDS,
            forward_fn=forward_to_frontend,
            stop_event=stop_event,
        )
        logger.info("meeting-bot watcher stopped")

    task = asyncio.create_task(_runner(), name="meeting-bot-watcher")
    return task
