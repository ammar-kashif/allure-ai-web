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


# ---------------------------------------------------------------------------
# Autonomy-pass helpers (Stage 1+2 of the autonomous follow-up plan).
#
# These manipulate the frontend SQLite `tasks` table directly. The backend
# is the source of truth for the autonomy audit (autonomy_runs +
# autonomy_actions in the backend DB); these helpers carry the FK
# (autonomy_action_id) into the frontend tasks row so undo can find the
# task again from the audit row.
# ---------------------------------------------------------------------------


def list_project_tasks(
    project_id: str,
    *,
    since_days: int = 60,
) -> list[dict[str, Any]]:
    """Return open + recent-by-creation tasks scoped to one project.

    Tasks live in the frontend DB and have no direct project_id column;
    the project link goes through `recordings.project_id`. Joins via
    `tasks.source_recording_id`.

    Returns rows as plain dicts. Empty list if the frontend DB isn't
    initialized yet.
    """
    conn = _open_frontend_db()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                t.id, t.title, t.detail, t.status, t.priority,
                t.assignee, t.source_outcome_id, t.source_recording_id,
                t.backlink, t.created_at
            FROM tasks t
            JOIN recordings r ON r.id = t.source_recording_id
            WHERE r.project_id = ?
              AND (
                t.status != 'done'
                OR t.created_at >= date('now', ?)
              )
            ORDER BY t.created_at DESC
            """,
            (project_id, f"-{int(since_days)} days"),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as exc:
        logger.warning("list_project_tasks failed for %s: %s", project_id, exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_task_with_audit_link(
    *,
    recording_id: str,
    title: str,
    assignee: str,
    detail: str = "",
    backlink: str = "",
    autonomy_action_id: str,
    autonomy_run_id: str,
    priority: str = "medium",
) -> dict[str, Any] | None:
    """Insert a row into the frontend `tasks` table on behalf of the
    autonomy pass. Status defaults to 'todo'. The `autonomy_action_id`
    and `autonomy_run_id` columns are added by the Stage-2 frontend
    migration (`src/lib/db/index.ts`).

    `recording_id` is the BACKEND job id. The frontend tasks table
    references the FRONTEND recording row id, so we resolve via
    `recordings.backend_id` first.

    Returns the inserted row or None on failure / missing DB.
    """
    conn = _open_frontend_db()
    if conn is None:
        return None
    import uuid as _uuid

    task_id = str(_uuid.uuid4())
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM recordings WHERE backend_id = ?",
            (recording_id,),
        )
        row = cur.fetchone()
        if row is None:
            logger.info(
                "create_task_with_audit_link: no frontend recording for backend_id=%s",
                recording_id,
            )
            return None
        local_recording_id = row[0]

        cur.execute(
            """
            INSERT INTO tasks (
                id, title, detail, source_recording_id,
                backlink, status, priority, assignee,
                autonomy_action_id, autonomy_run_id
            ) VALUES (?, ?, ?, ?, ?, 'todo', ?, ?, ?, ?)
            """,
            (
                task_id, title, detail, local_recording_id,
                backlink, priority, assignee,
                autonomy_action_id, autonomy_run_id,
            ),
        )
        conn.commit()
        return {
            "id": task_id,
            "title": title,
            "detail": detail,
            "source_recording_id": local_recording_id,
            "assignee": assignee,
            "status": "todo",
            "priority": priority,
            "backlink": backlink,
            "autonomy_action_id": autonomy_action_id,
            "autonomy_run_id": autonomy_run_id,
        }
    except Exception as exc:
        logger.warning(
            "create_task_with_audit_link failed for %s: %s",
            autonomy_action_id, exc,
        )
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def delete_task_by_autonomy_action_id(action_id: str) -> int:
    """Delete the autonomy-created task linked to this audit action.
    Returns rowcount (0 if not found / DB unavailable).
    """
    conn = _open_frontend_db()
    if conn is None:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM tasks WHERE autonomy_action_id = ?",
            (action_id,),
        )
        conn.commit()
        return cur.rowcount
    except Exception as exc:
        logger.warning(
            "delete_task_by_autonomy_action_id failed for %s: %s",
            action_id, exc,
        )
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass
