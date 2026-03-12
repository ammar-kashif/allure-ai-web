"""Pydantic request/response models for all endpoints."""

from typing import Literal

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Returned from POST /recordings."""

    id: str


class StatusResponse(BaseModel):
    """Returned from GET /recordings/{id}/status."""

    status: Literal["pending", "processing", "completed", "failed"]


class TranscriptSegment(BaseModel):
    """Individual transcript segment."""

    start: float
    end: float
    text: str
    speaker: str
    confidence: float


class SpeakerStats(BaseModel):
    """Per-speaker statistics."""

    label: str
    talk_time_pct: float
    utterance_count: int


class TranscriptResponse(BaseModel):
    """Full transcript response."""

    id: str
    duration: float
    language: str
    speakers: list[SpeakerStats]
    segments: list[TranscriptSegment]
