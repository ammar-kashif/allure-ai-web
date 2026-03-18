"""Pydantic request/response models for all endpoints."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Returned from POST /recordings."""

    id: str


class StatusResponse(BaseModel):
    """Returned from GET /recordings/{id}/status."""

    status: Literal["pending", "processing", "completed", "failed"]
    extraction_status: Literal[
        "none", "pending", "processing", "completed", "failed"
    ] = "none"


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
    talk_time: float
    word_count: int
    wpm: float
    turns: int
    avg_turn_duration: float
    pauses: int
    avg_pause_duration: float


class TranscriptResponse(BaseModel):
    """Full transcript response."""

    id: str
    duration: float
    language: str
    speakers: list[SpeakerStats]
    segments: list[TranscriptSegment]
    processing_time: float


# --- Extraction / Outcome models ---


class EvidenceRef(BaseModel):
    """Reference to a transcript segment as evidence for an outcome."""

    segment_index: int
    speaker: str
    timestamp: float
    text_snippet: str = ""


class Outcome(BaseModel):
    """A single extracted outcome."""

    id: str
    type: Literal["decision", "action_item", "requirement", "blocker"]
    title: str
    detail: str
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[EvidenceRef]
    promoted: bool = False
    promoted_id: Optional[str] = None


class OutcomesResponse(BaseModel):
    """Response for GET /recordings/{id}/outcomes."""

    job_id: str
    extraction_status: Literal[
        "none", "pending", "processing", "completed", "failed"
    ]
    outcomes: list[Outcome] = []


class PromoteResponse(BaseModel):
    """Response for POST /recordings/{id}/outcomes/{index}/promote."""

    id: str
    type: Literal["task", "requirement"]
    backlink: str


class AttachmentResponse(BaseModel):
    """Metadata for an attachment (no extracted_text)."""

    id: str
    recording_id: str
    filename: str
    file_type: str
    file_size: int
    extraction_error: Optional[str] = None
    created_at: str


class AttachmentTextResponse(BaseModel):
    """Extracted text content for an attachment."""

    id: str
    extracted_text: str
