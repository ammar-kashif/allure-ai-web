"""Forward a finalized bot recording into Allure's frontend upload endpoint.

The frontend's POST /api/recordings is the single entry point that creates
the user-facing recording row and proxies the file to the backend's
POST /recordings for STT + extraction. Going through it (vs. POSTing the
backend directly) ensures the recording shows up in the dashboard.
"""

import asyncio
import logging
import mimetypes
import os
from typing import Any, Optional

import httpx
import librosa

from meeting_bot.config import FRONTEND_URL

logger = logging.getLogger(__name__)


class ForwardError(RuntimeError):
    """Raised when the frontend permanently rejects or is unreachable."""


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _duration_ms(audio_path: str) -> int:
    """Best-effort duration probe; 0 on failure so we don't block the upload."""
    try:
        seconds = librosa.get_duration(path=audio_path)
        return int(round(seconds * 1000))
    except Exception as exc:
        logger.warning("librosa.get_duration failed for %s: %s", audio_path, exc)
        return 0


async def forward_to_frontend(
    audio_path: str,
    recording_id: str,
    title: str,
    project_id: Optional[str] = None,
    *,
    frontend_url: str = FRONTEND_URL,
    max_attempts: int = 3,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> dict[str, Any]:
    """POST the audio file to the frontend's /api/recordings as multipart.

    Retries on connection errors and 5xx up to max_attempts (linear backoff).
    4xx is treated as terminal -- raising immediately so we don't hammer the
    server with bad input.
    """
    if not os.path.isfile(audio_path):
        raise ForwardError(f"Audio file missing at forward time: {audio_path}")

    duration_ms = await asyncio.to_thread(_duration_ms, audio_path)
    filename = os.path.basename(audio_path)

    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            with open(audio_path, "rb") as f:
                file_bytes = f.read()

            data = {
                "recordingId": recording_id,
                "title": title,
                "durationMs": str(duration_ms),
            }
            if project_id:
                data["projectId"] = project_id

            files = {"file": (filename, file_bytes, _guess_mime(filename))}

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                transport=transport,
            ) as client:
                response = await client.post(
                    f"{frontend_url.rstrip('/')}/api/recordings",
                    data=data,
                    files=files,
                )

            if 200 <= response.status_code < 300:
                logger.info(
                    "Forwarded recording %s to frontend (%d bytes, %d ms duration)",
                    recording_id,
                    len(file_bytes),
                    duration_ms,
                )
                try:
                    return response.json()
                except ValueError:
                    return {"status": response.status_code}

            if 400 <= response.status_code < 500:
                raise ForwardError(
                    f"Frontend rejected (HTTP {response.status_code}): {response.text}"
                )

            # 5xx -> retryable
            last_error = ForwardError(
                f"Frontend 5xx (HTTP {response.status_code}): {response.text}"
            )
        except httpx.HTTPError as exc:
            last_error = exc

        if attempt < max_attempts:
            await asyncio.sleep(2 * attempt)

    raise ForwardError(
        f"Forward failed after {max_attempts} attempts: {last_error}"
    ) from last_error
