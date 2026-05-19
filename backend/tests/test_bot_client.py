"""Tests for the meeting-bot async HTTP client."""

import json

import httpx
import pytest

from meeting_bot.bot_client import BotClient, BotDispatchError


def _transport(handler):
    """Wrap a sync request handler in httpx.MockTransport."""
    return httpx.MockTransport(handler)


class TestInferPlatform:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://meet.google.com/abc-defg-hij", "google"),
            ("https://teams.microsoft.com/l/meetup-join/x", "microsoft"),
            ("https://teams.live.com/meet/12345", "microsoft"),
            ("https://us04web.zoom.us/j/123", "zoom"),
            ("https://zoom.com/j/123", "zoom"),
        ],
    )
    def test_known_hosts(self, url, expected):
        assert BotClient.infer_platform(url) == expected

    def test_unknown_host_raises(self):
        with pytest.raises(ValueError):
            BotClient.infer_platform("https://webex.com/join/123")


class TestDispatch:
    @pytest.mark.asyncio
    async def test_sends_expected_body_to_correct_path(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(202, json={"status": "processing"})

        client = BotClient(base_url="http://bot:3001", transport=_transport(handler))
        result = await client.dispatch(
            platform="google",
            meeting_url="https://meet.google.com/xyz",
            recording_id="rec-abc-12345678",
            title="Sync",
        )

        assert result == {"status": "processing"}
        assert captured["url"] == "http://bot:3001/google/join"
        assert captured["body"]["url"] == "https://meet.google.com/xyz"
        assert captured["body"]["userId"] == "rec-abc-12345678"
        assert captured["body"]["botId"] == "rec-abc-12345678"
        assert captured["body"]["name"] == "Sync"
        assert captured["body"]["teamId"] == "allure"

    @pytest.mark.asyncio
    async def test_default_name_when_no_title(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(202, json={})

        client = BotClient(transport=_transport(handler))
        await client.dispatch(
            platform="google",
            meeting_url="https://meet.google.com/x",
            recording_id="abcdef1234567890",
            title=None,
        )

        # Default form: Allure-<first 8 chars of recording_id>
        assert captured["body"]["name"] == "Allure-abcdef12"

    @pytest.mark.asyncio
    async def test_4xx_raises_dispatch_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="bad url")

        client = BotClient(transport=_transport(handler))
        with pytest.raises(BotDispatchError, match="400"):
            await client.dispatch(
                platform="google",
                meeting_url="https://meet.google.com/x",
                recording_id="rec-1",
            )

    @pytest.mark.asyncio
    async def test_connect_error_raises_dispatch_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("nope")

        client = BotClient(transport=_transport(handler))
        with pytest.raises(BotDispatchError, match="unreachable"):
            await client.dispatch(
                platform="google",
                meeting_url="https://meet.google.com/x",
                recording_id="rec-1",
            )

    @pytest.mark.asyncio
    async def test_unknown_platform_raises_value_error(self):
        client = BotClient()
        with pytest.raises(ValueError):
            await client.dispatch(
                platform="webex",
                meeting_url="https://example.com/x",
                recording_id="rec-1",
            )

    @pytest.mark.asyncio
    async def test_empty_body_returns_status_payload(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(202, content=b"")

        client = BotClient(transport=_transport(handler))
        result = await client.dispatch(
            platform="google",
            meeting_url="https://meet.google.com/x",
            recording_id="rec-1",
        )
        assert result == {"status": 202, "text": ""}


class TestIsBusy:
    @pytest.mark.asyncio
    async def test_true_when_data_is_1(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"success": True, "data": 1})

        client = BotClient(transport=_transport(handler))
        assert await client.is_busy() is True

    @pytest.mark.asyncio
    async def test_false_when_data_is_0(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"success": True, "data": 0})

        client = BotClient(transport=_transport(handler))
        assert await client.is_busy() is False

    @pytest.mark.asyncio
    async def test_legacy_raw_integer_payload(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=1)

        client = BotClient(transport=_transport(handler))
        assert await client.is_busy() is True

    @pytest.mark.asyncio
    async def test_unreachable_returns_busy_true(self):
        """Conservative default: don't ingest if we can't verify idle."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("nope")

        client = BotClient(transport=_transport(handler))
        assert await client.is_busy() is True

    @pytest.mark.asyncio
    async def test_non_json_returns_busy_true(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"<html>down for maintenance</html>")

        client = BotClient(transport=_transport(handler))
        assert await client.is_busy() is True
