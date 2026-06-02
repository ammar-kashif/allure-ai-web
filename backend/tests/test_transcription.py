"""Unit tests for transcription pipeline utility functions.

These tests exercise pure functions only -- no Moonshine or SpeechBrain models required.
"""

from unittest.mock import MagicMock, patch

import pytest

from transcription import (
    align_transcript_with_speakers,
    calculate_speaker_stats,
    merge_consecutive_segments,
    remap_speaker_labels,
    run_transcription,
)


# ---------------------------------------------------------------------------
# merge_consecutive_segments
# ---------------------------------------------------------------------------


def test_merge_consecutive_segments_same_speaker():
    """Two segments with same speaker merge into one with combined text."""
    segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello there", "speaker": "Speaker 1", "confidence": 0.9},
        {"start": 2.0, "end": 4.0, "text": "how are you", "speaker": "Speaker 1", "confidence": 0.8},
    ]
    merged = merge_consecutive_segments(segments)
    assert len(merged) == 1
    assert merged[0]["start"] == 0.0
    assert merged[0]["end"] == 4.0
    assert merged[0]["text"] == "Hello there how are you"
    assert merged[0]["confidence"] == pytest.approx(0.85)
    assert merged[0]["speaker"] == "Speaker 1"


def test_merge_different_speakers():
    """Two segments with different speakers remain separate."""
    segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello", "speaker": "Speaker 1", "confidence": 0.9},
        {"start": 2.0, "end": 4.0, "text": "Hi", "speaker": "Speaker 2", "confidence": 0.8},
    ]
    merged = merge_consecutive_segments(segments)
    assert len(merged) == 2
    assert merged[0]["text"] == "Hello"
    assert merged[1]["text"] == "Hi"


# ---------------------------------------------------------------------------
# remap_speaker_labels
# ---------------------------------------------------------------------------


def test_remap_speaker_labels():
    """Cluster labels are remapped to Speaker 1, Speaker 2 by first appearance."""
    segments = [
        {"start": 0.0, "end": 2.0, "text": "Hi", "speaker": "SPEAKER_00", "confidence": 0.9},
        {"start": 2.0, "end": 4.0, "text": "Hey", "speaker": "SPEAKER_01", "confidence": 0.8},
        {"start": 4.0, "end": 6.0, "text": "OK", "speaker": "SPEAKER_00", "confidence": 0.85},
    ]
    remapped = remap_speaker_labels(segments)
    assert remapped[0]["speaker"] == "Speaker 1"
    assert remapped[1]["speaker"] == "Speaker 2"
    assert remapped[2]["speaker"] == "Speaker 1"


# ---------------------------------------------------------------------------
# calculate_speaker_stats
# ---------------------------------------------------------------------------


def test_calculate_speaker_stats():
    """Correct talk_time_pct and utterance_count calculation."""
    segments = [
        {"start": 0.0, "end": 6.0, "text": "...", "speaker": "Speaker 1", "confidence": 0.9},
        {"start": 6.0, "end": 10.0, "text": "...", "speaker": "Speaker 2", "confidence": 0.8},
    ]
    stats = calculate_speaker_stats(segments, total_duration=10.0)
    assert len(stats) == 2
    # Speaker 1: 6s / 10s total talk = 60%
    assert stats[0]["label"] == "Speaker 1"
    assert stats[0]["talk_time_pct"] == 60.0
    assert stats[0]["utterance_count"] == 1
    # Speaker 2: 4s / 10s = 40%
    assert stats[1]["label"] == "Speaker 2"
    assert stats[1]["talk_time_pct"] == 40.0
    assert stats[1]["utterance_count"] == 1


def test_calculate_speaker_stats_filters_low_speakers():
    """Speakers with <1% talk time are excluded from results."""
    segments = [
        {"start": 0.0, "end": 99.0, "text": "long talk", "speaker": "Speaker 1", "confidence": 0.9},
        {"start": 99.0, "end": 99.05, "text": "tiny", "speaker": "Speaker 2", "confidence": 0.8},
    ]
    stats = calculate_speaker_stats(segments, total_duration=100.0)
    # Speaker 2 has 0.05s out of ~99.05s total talk => ~0.05% => filtered
    assert len(stats) == 1
    assert stats[0]["label"] == "Speaker 1"


# ---------------------------------------------------------------------------
# align_transcript_with_speakers
# ---------------------------------------------------------------------------


def test_align_transcript_with_speakers():
    """Correct speaker assignment by maximum overlap."""
    transcript = [
        {"start": 0.0, "end": 3.0, "text": "Hello", "confidence": 0.9},
        {"start": 3.0, "end": 6.0, "text": "World", "confidence": 0.8},
    ]
    diarization = [
        {"start": 0.0, "end": 2.5, "speaker": "SPEAKER_00"},
        {"start": 2.5, "end": 6.0, "speaker": "SPEAKER_01"},
    ]
    aligned = align_transcript_with_speakers(transcript, diarization)
    # Segment [0, 3): overlaps SPEAKER_00 for 2.5s, SPEAKER_01 for 0.5s => SPEAKER_00
    assert aligned[0]["speaker"] == "SPEAKER_00"
    # Segment [3, 6): overlaps SPEAKER_01 for 3.0s, SPEAKER_00 for 0s => SPEAKER_01
    assert aligned[1]["speaker"] == "SPEAKER_01"
    # Original fields preserved
    assert aligned[0]["text"] == "Hello"
    assert aligned[1]["confidence"] == 0.8


# ---------------------------------------------------------------------------
# AgglomerativeClustering replaces MeanShift
# ---------------------------------------------------------------------------


def test_diarizer_uses_agglomerative_clustering():
    """FastDiarizer.diarize() uses AgglomerativeClustering with correct params."""
    from transcription import FastDiarizer

    mock_encoder = MagicMock()
    # Simulate encoder returning 192-dim embeddings
    import numpy as np
    import torch

    mock_encoder.encode_batch.return_value = torch.tensor(
        np.random.randn(1, 192).astype(np.float32)
    )

    diarizer = FastDiarizer(encoder=mock_encoder, window_size=1.0, hop_size=0.5)

    with patch("transcription.AgglomerativeClustering") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.fit_predict.return_value = np.array([0, 0, 1, 1, 0])
        mock_cls.return_value = mock_instance

        with patch("transcription.librosa") as mock_librosa:
            # Return 3 seconds of audio at 16kHz
            mock_librosa.load.return_value = (np.zeros(48000, dtype=np.float32), 16000)
            diarizer.diarize("fake.wav")

        mock_cls.assert_called_once_with(
            n_clusters=None,
            distance_threshold=0.7,
            metric="cosine",
            linkage="average",
        )


# ---------------------------------------------------------------------------
# Extended calculate_speaker_stats
# ---------------------------------------------------------------------------


def test_extended_speaker_stats_two_speakers():
    """calculate_speaker_stats returns all extended fields for 2-speaker segments."""
    segments = [
        {"start": 0.0, "end": 5.0, "text": "Hello world how are you", "speaker": "Speaker 1", "confidence": 0.9},
        {"start": 5.0, "end": 8.0, "text": "I am fine thanks", "speaker": "Speaker 2", "confidence": 0.8},
        {"start": 8.0, "end": 12.0, "text": "Great to hear that today", "speaker": "Speaker 1", "confidence": 0.85},
    ]
    stats = calculate_speaker_stats(segments, total_duration=12.0)

    assert len(stats) == 2

    # Speaker 1: talk_time=9.0, word_count=10, 2 turns, 1 pause (gap from 5.0 to 8.0 = 3.0s)
    s1 = next(s for s in stats if s["label"] == "Speaker 1")
    assert s1["talk_time"] == pytest.approx(9.0)
    assert s1["word_count"] == 10
    assert s1["wpm"] == pytest.approx(10 / (9.0 / 60), rel=0.01)
    assert s1["turns"] == 2
    assert s1["avg_turn_duration"] == pytest.approx(4.5)
    assert s1["pauses"] == 1
    assert s1["avg_pause_duration"] == pytest.approx(3.0)

    # Speaker 2: talk_time=3.0, word_count=4, 1 turn, 0 pauses
    s2 = next(s for s in stats if s["label"] == "Speaker 2")
    assert s2["talk_time"] == pytest.approx(3.0)
    assert s2["word_count"] == 4
    assert s2["wpm"] == pytest.approx(4 / (3.0 / 60), rel=0.01)
    assert s2["turns"] == 1
    assert s2["avg_turn_duration"] == pytest.approx(3.0)
    assert s2["pauses"] == 0
    assert s2["avg_pause_duration"] == pytest.approx(0.0)


def test_extended_speaker_stats_single_speaker():
    """Single-speaker case: pauses=0, avg_pause_duration=0.0."""
    segments = [
        {"start": 0.0, "end": 10.0, "text": "Hello world", "speaker": "Speaker 1", "confidence": 0.9},
    ]
    stats = calculate_speaker_stats(segments, total_duration=10.0)

    assert len(stats) == 1
    s = stats[0]
    assert s["pauses"] == 0
    assert s["avg_pause_duration"] == pytest.approx(0.0)
    assert s["turns"] == 1
    assert s["word_count"] == 2


def test_extended_speaker_stats_zero_duration():
    """Zero-duration edge case: no division by zero."""
    segments = [
        {"start": 0.0, "end": 0.0, "text": "", "speaker": "Speaker 1", "confidence": 0.9},
    ]
    # Should not raise
    stats = calculate_speaker_stats(segments, total_duration=0.0)
    # With 0 talk time, speaker may be filtered out (< 1% threshold with 0/0)
    # Just verify no exception is raised
    assert isinstance(stats, list)


# ---------------------------------------------------------------------------
# run_transcription includes processing_time
# ---------------------------------------------------------------------------


def test_run_transcription_includes_processing_time():
    """run_transcription return dict includes processing_time."""
    with patch("transcription.get_job") as mock_get_job, \
         patch("transcription.librosa") as mock_librosa, \
         patch("transcription.transcribe_audio") as mock_transcribe, \
         patch.object(MagicMock(), "diarize") as _:

        mock_get_job.return_value = {"file_path": "/tmp/fake.wav"}
        mock_librosa.get_duration.return_value = 10.0
        mock_transcribe.return_value = [
            {"start": 0.0, "end": 5.0, "text": "Hello", "confidence": 0.9},
        ]

        mock_app_state = MagicMock()
        mock_app_state.diarizer.diarize.return_value = [
            {"start": 0.0, "end": 10.0, "speaker": "cluster_0"},
        ]

        result = run_transcription("job-1", mock_app_state)

        assert "processing_time" in result
        assert isinstance(result["processing_time"], float)
        assert result["processing_time"] >= 0

