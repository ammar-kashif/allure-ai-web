"""FastAPI router exposing meeting-bot dispatch and status endpoints."""

import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from meeting_bot import dispatch_store
from meeting_bot.bot_client import BotClient, BotDispatchError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Module-level singleton so route handlers can share one client. Replaced via
# FastAPI dependency overrides in tests.
_bot_client = BotClient()


def get_bot_client() -> BotClient:
    return _bot_client


class DispatchRequest(BaseModel):
    """POST /meetings/dispatch body."""

    meeting_url: str = Field(..., min_length=1)
    platform: Optional[str] = Field(
        default=None,
        description="One of google|microsoft|zoom. Inferred from URL if omitted.",
    )
    project_id: Optional[str] = None
    title: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Shown to other meeting participants in the bot's name.",
    )


class DispatchResponse(BaseModel):
    recording_id: str
    status: str
    platform: str
    bot_response: dict[str, Any] = {}


class DispatchStatusResponse(BaseModel):
    recording_id: str
    meeting_url: str
    platform: str
    project_id: Optional[str] = None
    title: Optional[str] = None
    status: str
    audio_path: Optional[str] = None
    dispatched_at: str
    finalized_at: Optional[str] = None
    error: Optional[str] = None


@router.post("/dispatch", status_code=202, response_model=DispatchResponse)
async def dispatch_meeting(
    body: DispatchRequest,
    bot: BotClient = Depends(get_bot_client),
):
    """Generate a recording_id, record the dispatch, and tell the bot to join.

    The recording is brought into Allure asynchronously by the filesystem
    watcher once the bot finishes writing the .wav.
    """
    try:
        platform = body.platform or BotClient.infer_platform(body.meeting_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    recording_id = str(uuid4())
    dispatch_store.create(
        recording_id=recording_id,
        meeting_url=body.meeting_url,
        platform=platform,
        project_id=body.project_id,
        title=body.title,
    )

    try:
        bot_response = await bot.dispatch(
            platform=platform,
            meeting_url=body.meeting_url,
            recording_id=recording_id,
            title=body.title,
        )
    except BotDispatchError as exc:
        dispatch_store.update(recording_id, status="failed", error=str(exc))
        # 502: we accepted the request but the upstream bot refused.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "Dispatched meeting recording_id=%s platform=%s url=%s",
        recording_id,
        platform,
        body.meeting_url,
    )
    return DispatchResponse(
        recording_id=recording_id,
        status="dispatched",
        platform=platform,
        bot_response=bot_response,
    )


@router.get("/{recording_id}", response_model=DispatchStatusResponse)
async def get_meeting_status(recording_id: str):
    row = dispatch_store.get(recording_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return DispatchStatusResponse(**row)
