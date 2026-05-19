"""Tests for the frontend forwarder."""

import os
import struct

import httpx
import pytest

from meeting_bot import forwarder
from meeting_bot.forwarder import ForwardError, forward_to_frontend


@pytest.fixture
def wav_file(tmp_path):
    """Minimal valid 1-second WAV at 16 kHz mono pcm_s16le."""
    path = tmp_path / "meeting.wav"
    num_samples = 16000
    sample_rate = 16000
    channels = 1
    bits = 16
    byte_rate = sample_rate * channels * bits // 8
    block_align = channels * bits // 8
    data_size = num_samples * block_align
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b"data",
        data_size,
    )
    path.write_bytes(header + b"\x00\x00" * num_samples)
    return str(path)


async def _no_sleep(_seconds):
    """Skip the backoff sleep in retry tests."""
    return None


@pytest.mark.asyncio
async def test_success_returns_frontend_response(wav_file):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content_type"] = request.headers.get("content-type", "")
        captured["body_size"] = len(request.content)
        return httpx.Response(201, json={"id": "rec-123"})

    result = await forward_to_frontend(
        audio_path=wav_file,
        recording_id="rec-123",
        title="POC test",
        project_id="proj-A",
        frontend_url="http://frontend",
        transport=httpx.MockTransport(handler),
    )

    assert result == {"id": "rec-123"}
    assert captured["url"] == "http://frontend/api/recordings"
    assert captured["content_type"].startswith("multipart/form-data")
    # Body should be larger than the bare audio file -- it carries form fields too.
    assert captured["body_size"] > os.path.getsize(wav_file)


@pytest.mark.asyncio
async def test_sends_required_fields(wav_file):
    """The frontend route requires recordingId, title, and the file field."""
    raw_bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        raw_bodies.append(request.content)
        return httpx.Response(201, json={})

    await forward_to_frontend(
        audio_path=wav_file,
        recording_id="rec-abc",
        title="Demo",
        frontend_url="http://frontend",
        transport=httpx.MockTransport(handler),
    )

    body = raw_bodies[0].decode("utf-8", errors="ignore")
    assert 'name="recordingId"' in body and "rec-abc" in body
    assert 'name="title"' in body and "Demo" in body
    assert 'name="durationMs"' in body
    assert 'name="file"' in body
    assert "meeting.wav" in body


@pytest.mark.asyncio
async def test_project_id_omitted_when_absent(wav_file):
    raw_bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        raw_bodies.append(request.content)
        return httpx.Response(201, json={})

    await forward_to_frontend(
        audio_path=wav_file,
        recording_id="rec-1",
        title="x",
        project_id=None,
        frontend_url="http://frontend",
        transport=httpx.MockTransport(handler),
    )

    assert 'name="projectId"' not in raw_bodies[0].decode("utf-8", errors="ignore")


@pytest.mark.asyncio
async def test_missing_file_raises_forward_error(tmp_path):
    with pytest.raises(ForwardError, match="missing"):
        await forward_to_frontend(
            audio_path=str(tmp_path / "nope.wav"),
            recording_id="rec-1",
            title="x",
        )


@pytest.mark.asyncio
async def test_4xx_is_terminal_no_retry(wav_file, monkeypatch):
    """Client errors should not be retried."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="bad request")

    monkeypatch.setattr(forwarder.asyncio, "sleep", _no_sleep)
    with pytest.raises(ForwardError, match="400"):
        await forward_to_frontend(
            audio_path=wav_file,
            recording_id="rec-1",
            title="x",
            frontend_url="http://frontend",
            transport=httpx.MockTransport(handler),
            max_attempts=3,
        )
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_5xx_retries_then_succeeds(wav_file, monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="busy")
        return httpx.Response(201, json={"id": "rec"})

    monkeypatch.setattr(forwarder.asyncio, "sleep", _no_sleep)
    result = await forward_to_frontend(
        audio_path=wav_file,
        recording_id="rec",
        title="x",
        frontend_url="http://frontend",
        transport=httpx.MockTransport(handler),
        max_attempts=3,
    )
    assert result == {"id": "rec"}
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_5xx_exhausts_attempts(wav_file, monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(502, text="bad gateway")

    monkeypatch.setattr(forwarder.asyncio, "sleep", _no_sleep)
    with pytest.raises(ForwardError, match="3 attempts"):
        await forward_to_frontend(
            audio_path=wav_file,
            recording_id="rec",
            title="x",
            frontend_url="http://frontend",
            transport=httpx.MockTransport(handler),
            max_attempts=3,
        )
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_connect_error_retried_then_raised(wav_file, monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(forwarder.asyncio, "sleep", _no_sleep)
    with pytest.raises(ForwardError, match="3 attempts"):
        await forward_to_frontend(
            audio_path=wav_file,
            recording_id="rec",
            title="x",
            frontend_url="http://frontend",
            transport=httpx.MockTransport(handler),
            max_attempts=3,
        )
    assert calls["n"] == 3
