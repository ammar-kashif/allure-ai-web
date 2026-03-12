"""Unit tests for transcription pipeline utility functions.

These tests exercise pure functions only -- no Moonshine or SpeechBrain models required.
"""

import pytest

from transcription import (
    align_transcript_with_speakers,
    calculate_speaker_stats,
    merge_consecutive_segments,
    remap_speaker_labels,
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
