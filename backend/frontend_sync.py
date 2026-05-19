"""Direct cross-process writes from backend to the Next.js frontend SQLite.

The polling-based sync (status route → prefetchTranscript → updateRecording)
proved fragile: it depends on React Query cache invalidation order, the
page being open, and uvicorn HMR not being mid-reload. When extraction
finishes on the backend we want the frontend to see the new title
immediately, regardless of what state the browser or dev server is in.

This module writes title/description straight into the frontend's
SQLite recordings row, clears its cached transcript blob so the UI
re-fetches fresh, and optionally renames the audio file on disk to
include a human-readable slug.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent

FRONTEND_DB_PATH = Path(
    os.environ.get(
        "FRONTEND_DB_PATH",
        str(_PROJECT_ROOT / "public" / "recordings" / "allure-frontend.db"),
    )
)


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title: str, max_length: int = 60) -> str:
    """Filesystem-safe slug. Lowercased, alphanumeric + hyphens only."""
    s = _SLUG_NON_ALNUM.sub("-", (title or "").lower()).strip("-")
    return s[:max_length] or "untitled"


def _open_frontend_db() -> sqlite3.Connection | None:
    """Open the Next.js SQLite or return None if it isn't there yet
    (frontend may not have run / DB may not be initialized)."""
    if not FRONTEND_DB_PATH.exists():
        logger.debug(
            "Frontend DB not found at %s; skipping cross-process sync",
            FRONTEND_DB_PATH,
        )
        return None
    try:
        conn = sqlite3.connect(str(FRONTEND_DB_PATH), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except Exception as exc:
        logger.warning("Failed to open frontend DB: %s", exc)
        return None


def push_metadata_to_frontend(
    backend_job_id: str,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Push title/description into the frontend recordings row whose
    backend_id matches `backend_job_id`. Respects the title_is_auto
    flag — a user-renamed title is not overwritten unless titleIsAuto
    is true. Also clears the cached transcript blob so the next
    /transcript fetch comes from backend.

    Returns a dict describing what was updated. Never raises.
    """
    out: dict[str, Any] = {
        "local_id": None,
        "title_updated": False,
        "description_updated": False,
        "cache_cleared": False,
    }

    conn = _open_frontend_db()
    if conn is None:
        return out

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title_is_auto FROM recordings WHERE backend_id = ?",
            (backend_job_id,),
        )
        row = cur.fetchone()
        if row is None:
            logger.info(
                "No frontend recording for backend_id=%s (no-op)",
                backend_job_id,
            )
            return out

        local_id, title_is_auto = row
        out["local_id"] = local_id

        sets: list[str] = []
        values: list[Any] = []

        if title and title.strip() and title_is_auto:
            sets.append("title = ?")
            values.append(title.strip())
            out["title_updated"] = True

        if description and description.strip():
            sets.append("description = ?")
            values.append(description.strip())
            out["description_updated"] = True

        # Always clear cached transcript so the page re-fetches fresh
        sets.append("transcript_data = NULL")
        out["cache_cleared"] = True

        if not (out["title_updated"] or out["description_updated"]):
            # Even if title/desc weren't updated (e.g. titleIsAuto=0), still
            # clear the cache so an updated transcript can be re-fetched.
            sets.append("updated_at = datetime('now')")
            cur.execute(
                f"UPDATE recordings SET {', '.join(sets)} WHERE id = ?",
                [local_id],
            )
            conn.commit()
            return out

        sets.append("updated_at = datetime('now')")
        values.append(local_id)
        cur.execute(
            f"UPDATE recordings SET {', '.join(sets)} WHERE id = ?",
            values,
        )
        conn.commit()
        logger.info(
            "Synced to frontend DB: backend_id=%s local_id=%s "
            "title=%s description=%s (titleIsAuto=%s)",
            backend_job_id,
            local_id,
            out["title_updated"],
            out["description_updated"],
            title_is_auto,
        )
        return out
    except Exception as exc:
        logger.warning(
            "push_metadata_to_frontend failed for %s: %s", backend_job_id, exc
        )
        return out
    finally:
        try:
            conn.close()
        except Exception:
            pass


def rename_audio_files(
    backend_job_id: str,
    title: str,
    backend_wav_path: str | None,
) -> dict[str, str | None]:
    """Rename the backend WAV and the frontend audio copy to use a
    slugified title. Updates the file_path columns in both DBs. Never
    raises — failures keep the original paths.

    Naming pattern: ``<slug>-<short_job_id>.<ext>``  e.g.
    ``language-and-comprehension-test-1bbc26eb.wav``
    """
    result: dict[str, str | None] = {
        "backend_wav": backend_wav_path,
        "frontend_audio": None,
    }

    if not title or not title.strip():
        return result

    slug = slugify(title)
    short_id = backend_job_id[:8] if len(backend_job_id) >= 8 else backend_job_id

    # ----- backend WAV rename -----
    if backend_wav_path and os.path.exists(backend_wav_path):
        dirname = os.path.dirname(backend_wav_path)
        ext = os.path.splitext(backend_wav_path)[1] or ".wav"
        new_name = f"{slug}-{short_id}{ext}"
        new_path = os.path.join(dirname, new_name)

        if new_path == backend_wav_path:
            pass  # already named correctly
        elif os.path.exists(new_path):
            logger.info(
                "Backend WAV target already exists, leaving %s in place",
                backend_wav_path,
            )
        else:
            try:
                shutil.move(backend_wav_path, new_path)
                result["backend_wav"] = new_path
                logger.info(
                    "Renamed backend WAV: %s -> %s", backend_wav_path, new_path
                )
            except Exception as exc:
                logger.warning("Backend WAV rename failed: %s", exc)

    # ----- frontend audio rename + DB update -----
    conn = _open_frontend_db()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, file_path FROM recordings WHERE backend_id = ?",
                (backend_job_id,),
            )
            row = cur.fetchone()
            if row:
                local_id, file_path = row
                if file_path and os.path.exists(file_path):
                    dirname = os.path.dirname(file_path)
                    ext = os.path.splitext(file_path)[1] or ".webm"
                    new_name = f"{slug}-{short_id}{ext}"
                    new_path = os.path.join(dirname, new_name)

                    if new_path == file_path:
                        result["frontend_audio"] = file_path
                    elif os.path.exists(new_path):
                        # Already renamed by an earlier run; just sync DB
                        cur.execute(
                            "UPDATE recordings SET file_path = ? WHERE id = ?",
                            (new_path, local_id),
                        )
                        conn.commit()
                        result["frontend_audio"] = new_path
                    else:
                        try:
                            shutil.move(file_path, new_path)
                            cur.execute(
                                "UPDATE recordings SET file_path = ?, "
                                "updated_at = datetime('now') WHERE id = ?",
                                (new_path, local_id),
                            )
                            conn.commit()
                            result["frontend_audio"] = new_path
                            logger.info(
                                "Renamed frontend audio: %s -> %s",
                                file_path,
                                new_path,
                            )
                        except Exception as exc:
                            logger.warning(
                                "Frontend audio rename failed: %s", exc
                            )
        except Exception as exc:
            logger.warning(
                "rename_audio_files frontend section failed for %s: %s",
                backend_job_id,
                exc,
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return result
