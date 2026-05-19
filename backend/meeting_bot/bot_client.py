"""Async HTTP client for the meeting-bot service.

Only the endpoints we actually use are wrapped: the per-platform `/join`
dispatch and `/isbusy` polling. Anything more exotic should just use
httpx directly.
"""

import logging
from typing import Any, Optional

import httpx

from meeting_bot.config import MEETING_BOT_URL
from meeting_bot.dispatch_store import VALID_PLATFORMS

logger = logging.getLogger(__name__)


class BotDispatchError(RuntimeError):
    """Raised when the bot rejects a dispatch (4xx or unreachable)."""


class BotClient:
    """Thin async wrapper over the meeting-bot HTTP API.

    The bot returns 202 immediately from /join and runs the recording in the
    background; success here means "the bot accepted the job", not "the bot
    finished recording". The watcher is responsible for finalization.
    """

    def __init__(
        self,
        base_url: str = MEETING_BOT_URL,
        timeout: float = 10.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    @staticmethod
    def infer_platform(meeting_url: str) -> str:
        """Map a meeting URL to the bot's platform path segment.

        Raises ValueError for unrecognized hosts.
        """
        url = meeting_url.lower()
        if "meet.google.com" in url:
            return "google"
        if "teams.microsoft.com" in url or "teams.live.com" in url:
            return "microsoft"
        if "zoom.us" in url or "zoom.com" in url:
            return "zoom"
        raise ValueError(f"Cannot infer platform from URL: {meeting_url!r}")

    async def dispatch(
        self,
        platform: str,
        meeting_url: str,
        recording_id: str,
        title: Optional[str] = None,
    ) -> dict[str, Any]:
        """Tell the bot to join a meeting.

        Returns the parsed JSON response body. The bot will write its
        recording to `LOCAL_RECORDINGS_DIR/<recording_id>/...` because we
        pass `userId=recording_id` -- the watcher exploits that mapping.
        """
        if platform not in VALID_PLATFORMS:
            raise ValueError(f"Unknown platform: {platform!r}")

        body = {
            "url": meeting_url,
            # Showing in the meeting participant list. Keep short.
            "name": title or f"Allure-{recording_id[:8]}",
            "teamId": "allure",
            "userId": recording_id,
            "botId": recording_id,
        }

        try:
            async with self._client() as client:
                response = await client.post(f"{self._base}/{platform}/join", json=body)
        except httpx.HTTPError as exc:
            raise BotDispatchError(f"Bot unreachable at {self._base}: {exc}") from exc

        if response.status_code >= 400:
            raise BotDispatchError(
                f"Bot rejected dispatch ({response.status_code}): {response.text}"
            )

        try:
            return response.json()
        except ValueError:
            # 202 with empty/non-JSON body is fine.
            return {"status": response.status_code, "text": response.text}

    async def stop_current_job(self) -> dict[str, Any]:
        """Ask the bot to gracefully exit the current meeting job.

        Hits the patched POST /jobs/stop endpoint on the bot. The bot's
        waitUntilMeetingEnds loop picks up the flag within ~3s, exits the
        meeting, finalizes the recording, and becomes idle (ready for the
        next dispatch -- no process restart needed).
        """
        try:
            async with self._client() as client:
                response = await client.post(f"{self._base}/jobs/stop")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise BotDispatchError(
                f"Bot stop request failed: {exc}"
            ) from exc

    async def is_busy(self) -> bool:
        """Return True if the bot reports an in-flight job, False otherwise.

        Network errors are treated as 'unknown' -> True so we don't ingest
        a half-written file when we can't actually verify the bot is idle.
        """
        try:
            async with self._client() as client:
                response = await client.get(f"{self._base}/isbusy")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("is_busy probe failed (treating as busy): %s", exc)
            return True
        except ValueError:
            logger.warning("is_busy returned non-JSON; treating as busy")
            return True

        # The bot wraps the boolean as either `{success: true, data: 0|1}` or
        # legacy `1`/`0` at the top level. Handle both.
        if isinstance(payload, dict):
            return bool(payload.get("data"))
        return bool(payload)
