"""Pydantic request/response models for all endpoints."""

from typing import Literal

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
    chart_status: Literal[
        "none", "pending", "processing", "completed", "failed"
    ] = "none"
    duration_ms: float | None = None


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
    role: str | None = None


class SpeakerRoleUpdateRequest(BaseModel):
    """Update inferred roles for speakers. Maps speaker label to new role."""

    roles: dict[str, str]


class TranscriptResponse(BaseModel):
    """Full transcript response."""

    id: str
    duration: float
    language: str
    speakers: list[SpeakerStats]
    segments: list[TranscriptSegment]


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
    promoted_id: str | None = None


class OutcomesResponse(BaseModel):
    """Response for GET /recordings/{id}/outcomes."""

    job_id: str
    extraction_status: Literal[
        "none", "pending", "processing", "completed", "failed"
    ]
    outcomes: list[Outcome] = []


class SpeakerRenameRequest(BaseModel):
    """Rename speakers in a transcript. Maps old label to new label."""

    renames: dict[str, str]


class DecisionChartResponse(BaseModel):
    """Returned from GET /recordings/{id}/chart."""

    job_id: str
    chart_status: Literal[
        "none", "pending", "processing", "completed", "failed"
    ]
    chart_plantuml: str | None = None


class PromoteRequest(BaseModel):
    """One-click promote request (empty body)."""

    pass


class PromoteResponse(BaseModel):
    """Response for POST /recordings/{id}/outcomes/{index}/promote."""

    id: str
    type: Literal["task", "requirement"]
    backlink: str
    title: str
    detail: str
