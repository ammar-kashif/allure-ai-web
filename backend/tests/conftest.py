"""Shared test fixtures."""

import os
import struct
import tempfile

import pytest

import storage
from job_queue import job_queue


@pytest.fixture
def sample_audio():
    """Create a minimal valid WAV file (1 second of silence at 16kHz mono 16-bit PCM)."""
    num_samples = 16000
    num_channels = 1
    sample_rate = 16000
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,  # chunk size
        1,  # PCM format
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    audio_data = b"\x00\x00" * num_samples  # silence

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(header)
        f.write(audio_data)
        path = f.name

    yield path

    if os.path.exists(path):
        os.remove(path)


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """Initialize a fresh temp SQLite DB and drain job queue before each test."""
    db_path = str(tmp_path / "test_allure.db")
    storage.init_db(db_path)

    # Drain queue (items are now tuples)
    while not job_queue.empty():
        try:
            job_queue.get_nowait()
            job_queue.task_done()
        except Exception:
            break

    # Ensure uploads directory exists (lifespan may not run in test transport)
    from main import UPLOADS_DIR

    os.makedirs(UPLOADS_DIR, exist_ok=True)
