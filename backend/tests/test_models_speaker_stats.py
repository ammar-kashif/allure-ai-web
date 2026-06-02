"""Unit tests for SpeakerStats model validation — custom_label and role fields."""

import pytest
from models import SpeakerStats, TranscriptResponse


# Shared base kwargs for a valid SpeakerStats (without custom_label/role)
BASE_STATS = {
    "label": "Speaker 1",
    "talk_time_pct": 45.5,
    "utterance_count": 12,
    "talk_time": 120.0,
    "word_count": 350,
    "wpm": 175.0,
    "turns": 6,
    "avg_turn_duration": 20.0,
    "pauses": 3,
    "avg_pause_duration": 2.5,
}


def test_speaker_stats_all_fields():
    """Test 1: SpeakerStats with all fields including custom_label and role validates."""
    stats = SpeakerStats(
        **BASE_STATS,
        custom_label="Alice",
        role="Interviewer",
    )
    assert stats.custom_label == "Alice"
    assert stats.role == "Interviewer"
    assert stats.label == "Speaker 1"


def test_speaker_stats_defaults_backward_compat():
    """Test 2: SpeakerStats without custom_label/role uses defaults — backward compat."""
    stats = SpeakerStats(**BASE_STATS)
    assert stats.custom_label == ""
    assert stats.role == "Participant"


def test_speaker_stats_empty_custom_label_explicit_role():
    """Test 3: SpeakerStats with empty string custom_label and explicit role validates."""
    stats = SpeakerStats(**BASE_STATS, custom_label="", role="Notetaker")
    assert stats.custom_label == ""
    assert stats.role == "Notetaker"


def test_transcript_response_with_speaker_fields():
    """Test 4: TranscriptResponse containing speakers with custom_label/role validates."""
    response = TranscriptResponse(
        id="test-123",
        duration=300.0,
        language="en",
        speakers=[
            SpeakerStats(**BASE_STATS, custom_label="Bob", role="Host"),
            SpeakerStats(**BASE_STATS, custom_label="", role="Participant"),
        ],
        segments=[],
        processing_time=5.0,
    )
    assert len(response.speakers) == 2
    assert response.speakers[0].custom_label == "Bob"
    assert response.speakers[0].role == "Host"
    assert response.speakers[1].custom_label == ""
    assert response.speakers[1].role == "Participant"

