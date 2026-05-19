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
import subprocess
import tempfile
from typing import Any, Optional

import httpx
import librosa

from meeting_bot.config import (
    FORWARD_TRANSCODE_BITRATE,
    FORWARD_TRANSCODE_ENABLED,
    FRONTEND_URL,
)

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


def _transcode_for_upload(
    src_path: str,
    *,
    bitrate: str = FORWARD_TRANSCODE_BITRATE,
) -> Optional[str]:
    """Resample src to 16 kHz mono MP3 at `bitrate`. Returns the temp path.

    Returns None on ffmpeg failure -- caller falls back to the raw source so
    one bad file can't take down the whole pipeline.
    """
    suffix = ".mp3"
    fd, dst_path = tempfile.mkstemp(suffix=suffix, prefix="allure-fwd-")
    os.close(fd)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "libmp3lame",
                "-b:a",
                bitrate,
                dst_path,
            ],
            check=True,
            capture_output=True,
        )
        return dst_path
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning(
            "Transcode failed for %s (falling back to raw upload): %s",
            src_path,
            exc,
        )
        try:
            os.unlink(dst_path)
        except OSError:
            pass
        return None


async def forward_to_frontend(
    audio_path: str,
    recording_id: str,
    title: str,
    project_id: Optional[str] = None,
    *,
    frontend_url: str = FRONTEND_URL,
    max_attempts: int = 3,
    transport: Optional[httpx.AsyncBaseTransport] = None,
    transcode_enabled: Optional[bool] = None,
) -> dict[str, Any]:
    """POST the audio file to the frontend's /api/recordings as multipart.

    When FORWARD_TRANSCODE_ENABLED (default true), the source audio is
    resampled to 16 kHz mono MP3 at FORWARD_TRANSCODE_BITRATE first -- the
    backend always normalizes to 16 kHz mono anyway, so this just cuts what
    crosses the wire. On ffmpeg failure we fall back to the raw source.

    Retries on connection errors and 5xx up to max_attempts (linear backoff).
    4xx is treated as terminal -- raising immediately so we don't hammer the
    server with bad input.
    """
    if not os.path.isfile(audio_path):
        raise ForwardError(f"Audio file missing at forward time: {audio_path}")

    duration_ms = await asyncio.to_thread(_duration_ms, audio_path)

    if transcode_enabled is None:
        transcode_enabled = FORWARD_TRANSCODE_ENABLED

    upload_path = audio_path
    transcoded_path: Optional[str] = None
    if transcode_enabled:
        transcoded_path = await asyncio.to_thread(_transcode_for_upload, audio_path)
        if transcoded_path:
            upload_path = transcoded_path
            logger.info(
                "Transcoded %s for upload: %d -> %d bytes",
                recording_id,
                os.path.getsize(audio_path),
                os.path.getsize(upload_path),
            )

    filename = os.path.basename(upload_path)

    try:
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                with open(upload_path, "rb") as f:
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
    finally:
        if transcoded_path:
            try:
                os.unlink(transcoded_path)
            except OSError:
                pass
