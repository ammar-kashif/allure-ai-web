"""First-class segments table.

Segments live inside `jobs.result.segments` JSON today, which is fine for
reads but useless for indexing, joining, or FTS5. This module mirrors
segments into a real table so:
    - FTS triggers can index transcript text
    - entity_mentions can FK against (recording_id, segment_index)
    - vector embeddings can join on segment_index

Backward compatibility: `jobs.result.segments` continues to be the canonical
write site (existing extraction / transcription code is unchanged). The
mirror is driven by `mirror_from_job_result()` which is called whenever
`update_job(result=...)` is invoked from the job worker, plus a startup
backfill for existing recordings.
"""

import sqlite3
from typing import Any, Optional

import storage


def init() -> None:
    """Create the segments table and triggers. Idempotent."""
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS segments (
            recording_id    TEXT NOT NULL,
            segment_index   INTEGER NOT NULL,
            start_seconds   REAL NOT NULL,
            end_seconds     REAL NOT NULL,
            speaker         TEXT,
            text            TEXT NOT NULL,
            confidence      REAL,
            PRIMARY KEY (recording_id, segment_index)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_segments_recording_time "
        "ON segments(recording_id, start_seconds)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_segments_speaker "
        "ON segments(recording_id, speaker)"
    )
    conn.commit()


def mirror_from_job_result(recording_id: str, result: dict[str, Any]) -> int:
    """Replace this recording's segments rows from a job.result payload.

    Returns the number of segments written. A None or empty segments list
    deletes any existing rows so the table stays consistent with reality.
    """
    if not isinstance(result, dict):
        return 0
    segments = result.get("segments") or []
    conn = storage._get_conn()
    conn.execute(
        "DELETE FROM segments WHERE recording_id = ?", (recording_id,)
    )
    if not segments:
        conn.commit()
        return 0
    rows = []
    for i, seg in enumerate(segments):
        rows.append(
            (
                recording_id,
                i,
                float(seg.get("start", 0.0)),
                float(seg.get("end", 0.0)),
                seg.get("speaker"),
                seg.get("text", ""),
                float(seg.get("confidence", 1.0)) if seg.get("confidence") is not None else None,
            )
        )
    conn.executemany(
        "INSERT INTO segments (recording_id, segment_index, start_seconds, "
        "end_seconds, speaker, text, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def list_segments(recording_id: str) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM segments WHERE recording_id = ? ORDER BY segment_index",
        (recording_id,),
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def get_segment_window(
    recording_id: str, t_start: float, t_end: float
) -> list[dict[str, Any]]:
    """Return segments whose timestamps overlap [t_start, t_end]."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM segments
        WHERE recording_id = ?
          AND start_seconds < ?
          AND end_seconds > ?
        ORDER BY segment_index
        """,
        (recording_id, t_end, t_start),
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def backfill_all_from_jobs() -> int:
    """One-time backfill: walk every completed job and mirror its segments.

    Idempotent (mirror_from_job_result deletes existing rows first).
    Returns count of recordings backfilled.
    """
    from storage import list_jobs

    count = 0
    for job in list_jobs():
        if job.get("status") != "completed":
            continue
        result = job.get("result")
        if not isinstance(result, dict):
            continue
        n = mirror_from_job_result(job["id"], result)
        if n > 0:
            count += 1
    return count


def delete_segments(recording_id: str) -> int:
    conn = storage._get_conn()
    cursor = conn.execute(
        "DELETE FROM segments WHERE recording_id = ?", (recording_id,)
    )
    conn.commit()
    return cursor.rowcount
