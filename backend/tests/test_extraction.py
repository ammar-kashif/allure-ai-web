"""Tests for the extraction module with mocked LLM."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import storage
from extraction import (
    EXTRACTION_SCHEMA,
    format_backlink,
    format_transcript_for_prompt,
    run_extraction,
)


# --- Fixtures ---


SAMPLE_SEGMENTS = [
    {
        "start": 0.0,
        "end": 5.0,
        "text": "Let's go with React for the frontend.",
        "speaker": "Speaker 1",
        "confidence": 0.95,
    },
    {
        "start": 5.5,
        "end": 10.0,
        "text": "I'll handle the API integration by Friday.",
        "speaker": "Speaker 2",
        "confidence": 0.90,
    },
    {
        "start": 10.5,
        "end": 15.0,
        "text": "We need to support offline mode.",
        "speaker": "Speaker 1",
        "confidence": 0.88,
    },
    {
        "start": 15.5,
        "end": 20.0,
        "text": "The CI pipeline is broken, blocking deploys.",
        "speaker": "Speaker 2",
        "confidence": 0.92,
    },
]

MOCK_LLM_RESPONSE = {
    "outcomes": [
        {
            "type": "decision",
            "title": "Use React for frontend",
            "detail": "Team agreed to use React for the frontend framework.",
            "confidence": 0.95,
            "evidence_refs": [
                {
                    "segment_index": 0,
                    "speaker": "Speaker 1",
                    "timestamp": 0.0,
                    "text_snippet": "Let's go with React",
                }
            ],
        },
        {
            "type": "action_item",
            "title": "API integration by Friday",
            "detail": "Speaker 2 will handle API integration by Friday.",
            "confidence": 0.90,
            "evidence_refs": [
                {
                    "segment_index": 1,
                    "speaker": "Speaker 2",
                    "timestamp": 5.5,
                }
            ],
        },
        {
            "type": "requirement",
            "title": "Offline mode support",
            "detail": "Application must support offline mode.",
            "confidence": 0.75,
            "evidence_refs": [
                {
                    "segment_index": 2,
                    "speaker": "Speaker 1",
                    "timestamp": 10.5,
                }
            ],
        },
        {
            "type": "blocker",
            "title": "CI pipeline broken",
            "detail": "CI pipeline is broken and blocking deployments.",
            "confidence": 0.92,
            "evidence_refs": [
                {
                    "segment_index": 3,
                    "speaker": "Speaker 2",
                    "timestamp": 15.5,
                }
            ],
        },
    ]
}


@pytest.fixture
def sample_job():
    """Create a completed job with transcript in storage via SQLite API."""
    job_id = "test-extraction-job"
    storage.create_job(job_id, "/fake/path.wav", "meeting.wav")
    storage.update_job(
        job_id,
        status="completed",
        result={
            "id": job_id,
            "duration": 20.0,
            "language": "en",
            "speakers": [],
            "segments": SAMPLE_SEGMENTS,
        },
        extraction_status="none",
        outcomes=[],
    )
    return job_id


@pytest.fixture
def mock_app_state():
    """Create a mock app_state with mocked LLM."""
    mock_llm = MagicMock()
    mock_llm.create_chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(MOCK_LLM_RESPONSE),
                }
            }
        ]
    }
    return SimpleNamespace(llm=mock_llm)


# --- Tests ---


def test_extraction_produces_outcomes(sample_job, mock_app_state):
    """Given a mocked LLM that returns valid JSON, run_extraction returns outcomes."""
    outcomes = run_extraction(sample_job, mock_app_state)

    assert len(outcomes) == 4
    for outcome in outcomes:
        assert "id" in outcome
        assert "type" in outcome
        assert "title" in outcome
        assert "detail" in outcome
        assert "confidence" in outcome
        assert "evidence_refs" in outcome
        assert outcome["type"] in (
            "decision",
            "action_item",
            "requirement",
            "blocker",
        )


def test_outcome_schema_validation(sample_job, mock_app_state):
    """Each outcome has all required fields with valid types."""
    outcomes = run_extraction(sample_job, mock_app_state)

    for outcome in outcomes:
        assert isinstance(outcome["id"], str)
        assert len(outcome["id"]) > 0
        assert isinstance(outcome["title"], str)
        assert isinstance(outcome["detail"], str)
        assert isinstance(outcome["confidence"], (int, float))
        assert 0 <= outcome["confidence"] <= 1
        assert isinstance(outcome["evidence_refs"], list)
        assert isinstance(outcome["promoted"], bool)
        assert outcome["promoted"] is False
        assert outcome["promoted_id"] is None


def test_invalid_segment_indices_filtered(sample_job, mock_app_state):
    """Outcomes with segment_index beyond transcript length are filtered out."""
    # Modify mock response to include out-of-range segment index
    bad_response = {
        "outcomes": [
            {
                "type": "decision",
                "title": "Some decision",
                "detail": "Detail here.",
                "confidence": 0.85,
                "evidence_refs": [
                    {
                        "segment_index": 0,
                        "speaker": "Speaker 1",
                        "timestamp": 0.0,
                    },
                    {
                        "segment_index": 99,  # Out of range
                        "speaker": "Speaker 1",
                        "timestamp": 100.0,
                    },
                    {
                        "segment_index": -1,  # Negative
                        "speaker": "Speaker 1",
                        "timestamp": 0.0,
                    },
                ],
            }
        ]
    }
    mock_app_state.llm.create_chat_completion.return_value = {
        "choices": [{"message": {"content": json.dumps(bad_response)}}]
    }

    outcomes = run_extraction(sample_job, mock_app_state)

    assert len(outcomes) == 1
    # Only the valid ref (index 0) should remain
    assert len(outcomes[0]["evidence_refs"]) == 1
    assert outcomes[0]["evidence_refs"][0]["segment_index"] == 0


def test_backlink_format():
    """format_backlink produces correct format."""
    result = format_backlink("Sprint Planning", 154.0, "Speaker 1")
    assert result == "From: Sprint Planning @ 2:34 -- Speaker 1"

    # Edge case: zero timestamp
    result = format_backlink("Meeting", 0.0, "Alice")
    assert result == "From: Meeting @ 0:00 -- Alice"

    # Edge case: exact minute
    result = format_backlink("Standup", 120.0, "Bob")
    assert result == "From: Standup @ 2:00 -- Bob"


def test_format_transcript_for_prompt():
    """Segments are formatted as '[index] mm:ss speaker: text' lines."""
    segments = [
        {"start": 0.0, "text": "Hello", "speaker": "Alice"},
        {"start": 65.5, "text": "World", "speaker": "Bob"},
    ]
    result = format_transcript_for_prompt(segments)
    lines = result.split("\n")
    assert len(lines) == 2
    assert lines[0] == "[0] 0:00 Alice: Hello"
    assert lines[1] == "[1] 1:05 Bob: World"


def test_extraction_schema_has_required_fields():
    """EXTRACTION_SCHEMA has the expected structure."""
    assert "outcomes" in EXTRACTION_SCHEMA["properties"]
    items_props = EXTRACTION_SCHEMA["properties"]["outcomes"]["items"]["properties"]
    assert "type" in items_props
    assert "title" in items_props
    assert "detail" in items_props
    assert "confidence" in items_props
    assert "evidence_refs" in items_props

