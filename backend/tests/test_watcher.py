"""Tests for the meeting-bot filesystem watcher."""

import asyncio
import datetime as dt
import os
import time
from typing import Optional

import pytest

from meeting_bot import dispatch_store, watcher
from meeting_bot.forwarder import ForwardError


@pytest.fixture(autouse=True)
def _init_dispatches():
    dispatch_store.init()


@pytest.fixture(autouse=True)
def _fast_stability(monkeypatch):
    """Shrink the stability window so tests don't wait several seconds."""
    monkeypatch.setattr(watcher, "FILE_STABILITY_SECONDS", 0.01)


class FakeBot:
    """Stand-in BotClient with a controllable busy state."""

    def __init__(self, busy: bool = False):
        self.busy = busy
        self.calls = 0

    async def is_busy(self) -> bool:
        self.calls += 1
        return self.busy


def _write(path: str, content: bytes = b"x" * 1024) -> None:
    with open(path, "wb") as f:
        f.write(content)


async def _run_ticks(
    rec_dir: str,
    rows: list[dict],
    bot: FakeBot,
    forward_calls: list[dict],
    *,
    snapshots: Optional[dict] = None,
):
    """Convenience: run `_handle_dispatch` for each row in `rows`."""
    snapshots = snapshots if snapshots is not None else {}

    async def fake_forward(*, audio_path, recording_id, title, project_id):
        forward_calls.append(
            {
                "audio_path": audio_path,
                "recording_id": recording_id,
                "title": title,
                "project_id": project_id,
            }
        )
        return {"id": recording_id}

    for row in rows:
        await watcher._handle_dispatch(
            row,
            bot=bot,
            last_snapshots=snapshots,
            recordings_dir=rec_dir,
            forward_fn=fake_forward,
        )
    return snapshots


@pytest.mark.asyncio
async def test_no_action_when_directory_missing(tmp_path):
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    bot = FakeBot(busy=False)
    forwards: list[dict] = []
    await _run_ticks(str(tmp_path), [row], bot, forwards)
    assert forwards == []
    # Still 'dispatched' because nothing showed up on disk yet.
    assert dispatch_store.get("rec-1")["status"] == "dispatched"


@pytest.mark.asyncio
async def test_status_moves_to_recording_on_first_file_sighting(tmp_path):
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    rec_dir = tmp_path / "rec-1"
    rec_dir.mkdir()
    _write(str(rec_dir / "Google Meet - x - t.wav"))

    bot = FakeBot(busy=True)  # not idle yet -> shouldn't forward
    forwards: list[dict] = []
    await _run_ticks(str(tmp_path), [row], bot, forwards)

    assert forwards == []
    updated = dispatch_store.get("rec-1")
    assert updated["status"] == "recording"
    assert updated["audio_path"].endswith(".wav")


@pytest.mark.asyncio
async def test_skips_when_tmp_sibling_present(tmp_path):
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    rec_dir = tmp_path / "rec-1"
    rec_dir.mkdir()
    wav = rec_dir / "a.wav"
    _write(str(wav))
    _write(str(rec_dir / "a.tmp.webm"))  # ffmpeg still finalizing

    bot = FakeBot(busy=False)
    forwards: list[dict] = []

    # Two ticks so the snapshot is stable, then expect skip due to tmp sibling.
    snaps: dict = {}
    await _run_ticks(str(tmp_path), [row], bot, forwards, snapshots=snaps)
    await asyncio.sleep(0.05)
    await _run_ticks(
        str(tmp_path),
        [dispatch_store.get("rec-1")],
        bot,
        forwards,
        snapshots=snaps,
    )
    assert forwards == []


@pytest.mark.asyncio
async def test_skips_when_bot_busy(tmp_path):
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    rec_dir = tmp_path / "rec-1"
    rec_dir.mkdir()
    _write(str(rec_dir / "a.wav"))

    bot = FakeBot(busy=True)
    forwards: list[dict] = []

    snaps: dict = {}
    await _run_ticks(str(tmp_path), [row], bot, forwards, snapshots=snaps)
    await asyncio.sleep(0.05)
    await _run_ticks(
        str(tmp_path),
        [dispatch_store.get("rec-1")],
        bot,
        forwards,
        snapshots=snaps,
    )
    assert forwards == []


@pytest.mark.asyncio
async def test_full_path_to_ingested(tmp_path):
    """Two ticks with a stable WAV + idle bot -> forwarded + ingested."""
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
        project_id="proj-A",
        title="POC test",
    )
    rec_dir = tmp_path / "rec-1"
    rec_dir.mkdir()
    audio = rec_dir / "Google Meet - x - t.wav"
    _write(str(audio))

    # Backdate mtime so the stability check passes immediately.
    old = time.time() - 5
    os.utime(str(audio), (old, old))

    bot = FakeBot(busy=False)
    forwards: list[dict] = []

    snaps: dict = {}
    # First tick: marks 'recording', records snapshot.
    await _run_ticks(str(tmp_path), [row], bot, forwards, snapshots=snaps)
    # Second tick: stable + idle -> forward.
    await _run_ticks(
        str(tmp_path),
        [dispatch_store.get("rec-1")],
        bot,
        forwards,
        snapshots=snaps,
    )

    assert len(forwards) == 1
    assert forwards[0]["recording_id"] == "rec-1"
    assert forwards[0]["project_id"] == "proj-A"
    assert forwards[0]["title"] == "POC test"
    assert forwards[0]["audio_path"] == str(audio)

    final = dispatch_store.get("rec-1")
    assert final["status"] == "ingested"
    assert final["finalized_at"] is not None


@pytest.mark.asyncio
async def test_forward_error_marks_failed(tmp_path, monkeypatch):
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    rec_dir = tmp_path / "rec-1"
    rec_dir.mkdir()
    audio = rec_dir / "a.wav"
    _write(str(audio))
    old = time.time() - 5
    os.utime(str(audio), (old, old))

    async def boom(*, audio_path, recording_id, title, project_id):
        raise ForwardError("frontend down")

    bot = FakeBot(busy=False)
    snaps: dict = {}
    # Stamp snapshot.
    await watcher._handle_dispatch(
        row,
        bot=bot,
        last_snapshots=snaps,
        recordings_dir=str(tmp_path),
        forward_fn=boom,
    )
    # Now stable + idle.
    await watcher._handle_dispatch(
        dispatch_store.get("rec-1"),
        bot=bot,
        last_snapshots=snaps,
        recordings_dir=str(tmp_path),
        forward_fn=boom,
    )

    final = dispatch_store.get("rec-1")
    assert final["status"] == "failed"
    assert "frontend down" in final["error"]


@pytest.mark.asyncio
async def test_timeout_marks_failed(tmp_path, monkeypatch):
    """A dispatch older than MAX_RECORDING_MINUTES is failed without ingesting."""
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    # Backdate the dispatched_at to before the timeout window.
    import storage

    conn = storage._get_conn()
    long_ago = (dt.datetime.utcnow() - dt.timedelta(hours=4)).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE dispatches SET dispatched_at = ? WHERE recording_id = ?",
        (long_ago, "rec-1"),
    )
    conn.commit()

    monkeypatch.setattr(watcher, "MAX_RECORDING_MINUTES", 60)

    bot = FakeBot(busy=False)
    forwards: list[dict] = []
    await _run_ticks(str(tmp_path), [dispatch_store.get("rec-1")], bot, forwards)

    assert forwards == []
    final = dispatch_store.get("rec-1")
    assert final["status"] == "failed"
    assert "timeout" in final["error"]


@pytest.mark.asyncio
async def test_picks_newest_audio_when_multiple(tmp_path):
    row = dispatch_store.create(
        recording_id="rec-1",
        meeting_url="https://meet.google.com/x",
        platform="google",
    )
    rec_dir = tmp_path / "rec-1"
    rec_dir.mkdir()
    older = rec_dir / "a.wav"
    newer = rec_dir / "b-with-audio.mp4"
    _write(str(older))
    time.sleep(0.01)
    _write(str(newer))

    bot = FakeBot(busy=True)
    forwards: list[dict] = []
    await _run_ticks(str(tmp_path), [row], bot, forwards)

    chosen = dispatch_store.get("rec-1")["audio_path"]
    assert chosen.endswith("b-with-audio.mp4")


def test_find_candidate_audio_ignores_tmp_files(tmp_path):
    rec_dir = tmp_path / "rec"
    rec_dir.mkdir()
    _write(str(rec_dir / "Google Meet.tmp.webm"))
    _write(str(rec_dir / ".hidden.wav"))
    assert watcher._find_candidate_audio(str(rec_dir)) is None

    real = rec_dir / "Google Meet.wav"
    _write(str(real))
    assert watcher._find_candidate_audio(str(rec_dir)) == str(real)
