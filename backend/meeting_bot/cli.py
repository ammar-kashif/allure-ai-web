"""Tiny CLI for dispatching meeting recordings to the bot via Allure.

Usage:
    python -m meeting_bot.cli dispatch \\
        --url https://meet.google.com/abc-defg-hij \\
        [--title "Sprint review"] \\
        [--project-id proj-A] \\
        [--platform google|microsoft|zoom]

    python -m meeting_bot.cli status <recording_id>

The CLI is just a thin wrapper over the FastAPI endpoints so a human can
demo the POC without standing up the frontend UI.
"""

import argparse
import json
import sys
from typing import Optional

import httpx

DEFAULT_BACKEND = "http://localhost:8000"


def _dispatch(
    backend: str,
    meeting_url: str,
    title: Optional[str],
    project_id: Optional[str],
    platform: Optional[str],
) -> int:
    body: dict[str, str] = {"meeting_url": meeting_url}
    if title:
        body["title"] = title
    if project_id:
        body["project_id"] = project_id
    if platform:
        body["platform"] = platform

    try:
        response = httpx.post(f"{backend}/meetings/dispatch", json=body, timeout=30.0)
    except httpx.HTTPError as exc:
        print(f"ERROR: backend unreachable at {backend}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(response.json(), indent=2))
    return 0 if response.status_code < 400 else 1


def _status(backend: str, recording_id: str) -> int:
    try:
        response = httpx.get(f"{backend}/meetings/{recording_id}", timeout=15.0)
    except httpx.HTTPError as exc:
        print(f"ERROR: backend unreachable at {backend}: {exc}", file=sys.stderr)
        return 2

    if response.status_code == 404:
        print(f"No dispatch found with id={recording_id}", file=sys.stderr)
        return 1

    print(json.dumps(response.json(), indent=2))
    return 0 if response.status_code < 400 else 1


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="meeting-bot")
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help=f"Allure backend base URL (default: {DEFAULT_BACKEND})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_dispatch = sub.add_parser("dispatch", help="Tell the bot to join a meeting")
    p_dispatch.add_argument("--url", required=True, help="Meeting URL")
    p_dispatch.add_argument("--title", help="Recording title (also shown in meeting)")
    p_dispatch.add_argument("--project-id", help="Allure project id to assign")
    p_dispatch.add_argument(
        "--platform",
        choices=("google", "microsoft", "zoom"),
        help="Override platform inference",
    )

    p_status = sub.add_parser("status", help="Check a dispatched meeting's status")
    p_status.add_argument("recording_id")

    args = parser.parse_args(argv)

    if args.command == "dispatch":
        return _dispatch(
            args.backend, args.url, args.title, args.project_id, args.platform
        )
    if args.command == "status":
        return _status(args.backend, args.recording_id)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
