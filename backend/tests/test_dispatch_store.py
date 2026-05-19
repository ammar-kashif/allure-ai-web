"""Tests for the meeting-bot dispatch SQLite store."""

import pytest

from meeting_bot import dispatch_store


@pytest.fixture(autouse=True)
def _init_dispatches():
    """Ensure the dispatches table exists for each test.

    `conftest.reset_state` already calls storage.init_db() with a tmp path,
    so we only need to add our own table on top of that fresh DB.
    """
    dispatch_store.init()


class TestDispatchStore:
    def test_create_returns_row_with_defaults(self):
        row = dispatch_store.create(
            recording_id="rec-1",
            meeting_url="https://meet.google.com/abc",
            platform="google",
        )
        assert row["recording_id"] == "rec-1"
        assert row["meeting_url"] == "https://meet.google.com/abc"
        assert row["platform"] == "google"
        assert row["status"] == "dispatched"
        assert row["project_id"] is None
        assert row["title"] is None
        assert row["audio_path"] is None
        assert row["finalized_at"] is None
        assert row["error"] is None
        assert row["dispatched_at"]  # set by SQLite default

    def test_create_with_optional_fields(self):
        row = dispatch_store.create(
            recording_id="rec-2",
            meeting_url="https://teams.microsoft.com/x",
            platform="microsoft",
            project_id="proj-A",
            title="Sprint sync",
        )
        assert row["project_id"] == "proj-A"
        assert row["title"] == "Sprint sync"
        assert row["platform"] == "microsoft"

    def test_create_rejects_unknown_platform(self):
        with pytest.raises(ValueError):
            dispatch_store.create(
                recording_id="rec-3",
                meeting_url="https://example.com/x",
                platform="webex",
            )

    def test_get_returns_none_for_missing(self):
        assert dispatch_store.get("does-not-exist") is None

    def test_update_changes_fields(self):
        dispatch_store.create(
            recording_id="rec-4",
            meeting_url="https://zoom.us/j/1",
            platform="zoom",
        )
        updated = dispatch_store.update(
            "rec-4",
            status="recording",
            audio_path="/tmp/x.wav",
        )
        assert updated["status"] == "recording"
        assert updated["audio_path"] == "/tmp/x.wav"

    def test_update_rejects_invalid_status(self):
        dispatch_store.create(
            recording_id="rec-5",
            meeting_url="https://meet.google.com/y",
            platform="google",
        )
        with pytest.raises(ValueError):
            dispatch_store.update("rec-5", status="garbage")

    def test_update_missing_raises_keyerror(self):
        with pytest.raises(KeyError):
            dispatch_store.update("missing", status="ingested")

    def test_list_pending_filters_terminal_states(self):
        dispatch_store.create(
            recording_id="p-1",
            meeting_url="https://meet.google.com/a",
            platform="google",
        )
        dispatch_store.create(
            recording_id="p-2",
            meeting_url="https://meet.google.com/b",
            platform="google",
        )
        dispatch_store.create(
            recording_id="p-3",
            meeting_url="https://meet.google.com/c",
            platform="google",
        )
        dispatch_store.update("p-2", status="ingested")
        dispatch_store.update("p-3", status="failed", error="bot timeout")

        pending = dispatch_store.list_pending()
        ids = [r["recording_id"] for r in pending]
        assert ids == ["p-1"]

    def test_list_pending_includes_recording_and_forwarding(self):
        dispatch_store.create(
            recording_id="r-1",
            meeting_url="https://meet.google.com/a",
            platform="google",
        )
        dispatch_store.create(
            recording_id="r-2",
            meeting_url="https://meet.google.com/b",
            platform="google",
        )
        dispatch_store.update("r-1", status="recording")
        dispatch_store.update("r-2", status="forwarding")

        ids = {r["recording_id"] for r in dispatch_store.list_pending()}
        assert ids == {"r-1", "r-2"}

    def test_delete_returns_true_then_false(self):
        dispatch_store.create(
            recording_id="d-1",
            meeting_url="https://meet.google.com/d",
            platform="google",
        )
        assert dispatch_store.delete("d-1") is True
        assert dispatch_store.delete("d-1") is False
        assert dispatch_store.get("d-1") is None
