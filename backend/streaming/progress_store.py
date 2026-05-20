"""SQLite-backed progress store for streaming audio ingestion.

Two tables:
    chunk_progress         -- one row per (recording_id, chunk_seq) chunk file
    recording_pipeline_state -- one row per recording, tracks aggregate stage

The progress table is the durable record of what has been processed. A
trigger maintains aggregate counts on the pipeline-state row so app code
doesn't have to keep them in sync manually -- the trigger is the SQLite
equivalent of a stored procedure for that bookkeeping.

Idempotency: each chunk row carries a sha256 of the file bytes. A chunk
delivered twice (e.g. after a watcher restart) hits the unique constraint
on (recording_id, sha256, pipeline_version) and is treated as a no-op.

State machine for `chunk_progress.state`:
    queued -> processing -> done
                         \\-> failed (terminal until pipeline_version bumps)

State machine for `recording_pipeline_state.stage`:
    streaming         -- chunks arriving and being processed
    awaiting_finalize -- bot left meeting, no more chunks expected
    finalizing        -- global diarization clustering running
    finalized         -- diarization done, ready for outcome extraction
    extracting        -- extraction LLM call running
    completed         -- end of pipeline
    failed            -- any terminal error
"""

import datetime as dt
import sqlite3
from typing import Any, Optional

import storage

VALID_CHUNK_STATES = {"queued", "processing", "done", "failed"}
VALID_PIPELINE_STAGES = {
    "streaming",
    "awaiting_finalize",
    "finalizing",
    "finalized",
    "extracting",
    "completed",
    "failed",
}


def init() -> None:
    """Create tables, indexes, and the counter trigger if missing."""
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunk_progress (
            recording_id        TEXT NOT NULL,
            chunk_seq           INTEGER NOT NULL,
            chunk_path          TEXT NOT NULL,
            byte_offset_start   INTEGER NOT NULL DEFAULT 0,
            byte_offset_end     INTEGER NOT NULL DEFAULT 0,
            seconds_start       REAL NOT NULL DEFAULT 0,
            seconds_end         REAL NOT NULL DEFAULT 0,
            sha256              TEXT NOT NULL,
            pipeline_version    INTEGER NOT NULL DEFAULT 1,
            state               TEXT NOT NULL DEFAULT 'queued',
            error               TEXT,
            stt_segments_json   TEXT,
            embeddings_path     TEXT,
            embeddings_meta_json TEXT,
            created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            PRIMARY KEY (recording_id, chunk_seq, pipeline_version)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunk_progress_recording "
        "ON chunk_progress(recording_id, state)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunk_progress_sha "
        "ON chunk_progress(recording_id, sha256, pipeline_version)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recording_pipeline_state (
            recording_id        TEXT PRIMARY KEY,
            stage               TEXT NOT NULL DEFAULT 'streaming',
            pipeline_version    INTEGER NOT NULL DEFAULT 1,
            chunks_total        INTEGER NOT NULL DEFAULT 0,
            chunks_done         INTEGER NOT NULL DEFAULT 0,
            total_seconds       REAL NOT NULL DEFAULT 0,
            finalized_at        TEXT,
            error               TEXT,
            created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )

    # Trigger: when a chunk transitions into 'done', bump the aggregate
    # counters on the pipeline-state row. App code never has to remember.
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chunk_progress_after_done
        AFTER UPDATE OF state ON chunk_progress
        WHEN NEW.state = 'done' AND OLD.state <> 'done'
        BEGIN
            UPDATE recording_pipeline_state
            SET chunks_done = chunks_done + 1,
                total_seconds = total_seconds + (NEW.seconds_end - NEW.seconds_start),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE recording_id = NEW.recording_id;
        END
        """
    )

    # Trigger: keep chunks_total in sync on insert / version bump.
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chunk_progress_after_insert
        AFTER INSERT ON chunk_progress
        BEGIN
            UPDATE recording_pipeline_state
            SET chunks_total = chunks_total + 1,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE recording_id = NEW.recording_id;
        END
        """
    )
    conn.commit()


def _now_iso() -> str:
    """Match SQLite strftime('%Y-%m-%dT%H:%M:%fZ', 'now') format (ms precision)
    so string-ordered comparisons against default-populated rows are correct."""
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------------------
# recording_pipeline_state
# ---------------------------------------------------------------------------


def ensure_recording(recording_id: str, stage: str = "streaming") -> dict[str, Any]:
    """Create the pipeline-state row if missing. Idempotent."""
    if stage not in VALID_PIPELINE_STAGES:
        raise ValueError(f"Invalid stage: {stage!r}")
    conn = storage._get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO recording_pipeline_state (recording_id, stage) "
        "VALUES (?, ?)",
        (recording_id, stage),
    )
    conn.commit()
    return get_state(recording_id)  # type: ignore[return-value]


def get_state(recording_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM recording_pipeline_state WHERE recording_id = ?",
        (recording_id,),
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def update_state(recording_id: str, **fields: Any) -> dict[str, Any]:
    if "stage" in fields and fields["stage"] not in VALID_PIPELINE_STAGES:
        raise ValueError(f"Invalid stage: {fields['stage']!r}")
    fields["updated_at"] = _now_iso()
    conn = storage._get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [recording_id]
    cursor = conn.execute(
        f"UPDATE recording_pipeline_state SET {sets} WHERE recording_id = ?",
        values,
    )
    if cursor.rowcount == 0:
        raise KeyError(f"Pipeline state for {recording_id} not found")
    conn.commit()
    return get_state(recording_id)  # type: ignore[return-value]


def list_unfinished_recordings() -> list[dict[str, Any]]:
    """Recordings still mid-pipeline. Used by the worker resume logic."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM recording_pipeline_state "
        "WHERE stage NOT IN ('completed', 'failed') "
        "ORDER BY updated_at"
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def bump_pipeline_version(recording_id: str) -> int:
    """Increment pipeline_version and reset counters for a full re-process.

    Existing chunk_progress rows at the previous version stay around for
    audit but are ignored by new processing.
    """
    conn = storage._get_conn()
    cursor = conn.execute(
        """
        UPDATE recording_pipeline_state
        SET pipeline_version = pipeline_version + 1,
            chunks_total = 0,
            chunks_done = 0,
            total_seconds = 0,
            stage = 'streaming',
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE recording_id = ?
        """,
        (recording_id,),
    )
    if cursor.rowcount == 0:
        raise KeyError(f"Pipeline state for {recording_id} not found")
    conn.commit()
    row = conn.execute(
        "SELECT pipeline_version FROM recording_pipeline_state WHERE recording_id = ?",
        (recording_id,),
    ).fetchone()
    return int(row[0])


# ---------------------------------------------------------------------------
# chunk_progress
# ---------------------------------------------------------------------------


def upsert_chunk(
    recording_id: str,
    chunk_seq: int,
    chunk_path: str,
    sha256: str,
    *,
    pipeline_version: int = 1,
    seconds_start: float = 0.0,
    seconds_end: float = 0.0,
    byte_offset_start: int = 0,
    byte_offset_end: int = 0,
) -> dict[str, Any]:
    """Insert a chunk row if absent. If a row already exists at the same
    (recording_id, chunk_seq, pipeline_version), it is returned unchanged --
    this is the idempotency guarantee for duplicate deliveries.
    """
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    try:
        existing = conn.execute(
            "SELECT * FROM chunk_progress "
            "WHERE recording_id = ? AND chunk_seq = ? AND pipeline_version = ?",
            (recording_id, chunk_seq, pipeline_version),
        ).fetchone()
        if existing:
            return dict(existing)

        # Also dedupe on sha256 within the same recording + version -- the
        # same chunk delivered under a different seq number is still the
        # same chunk.
        by_sha = conn.execute(
            "SELECT * FROM chunk_progress "
            "WHERE recording_id = ? AND sha256 = ? AND pipeline_version = ?",
            (recording_id, sha256, pipeline_version),
        ).fetchone()
        if by_sha:
            return dict(by_sha)
    finally:
        conn.row_factory = None

    conn.execute(
        """
        INSERT INTO chunk_progress (
            recording_id, chunk_seq, chunk_path, byte_offset_start,
            byte_offset_end, seconds_start, seconds_end, sha256,
            pipeline_version, state
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued')
        """,
        (
            recording_id,
            chunk_seq,
            chunk_path,
            byte_offset_start,
            byte_offset_end,
            seconds_start,
            seconds_end,
            sha256,
            pipeline_version,
        ),
    )
    conn.commit()
    return get_chunk(recording_id, chunk_seq, pipeline_version)  # type: ignore[return-value]


def _row_to_chunk(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def get_chunk(
    recording_id: str, chunk_seq: int, pipeline_version: int = 1
) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM chunk_progress "
        "WHERE recording_id = ? AND chunk_seq = ? AND pipeline_version = ?",
        (recording_id, chunk_seq, pipeline_version),
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def update_chunk(
    recording_id: str,
    chunk_seq: int,
    pipeline_version: int = 1,
    **fields: Any,
) -> dict[str, Any]:
    if "state" in fields and fields["state"] not in VALID_CHUNK_STATES:
        raise ValueError(f"Invalid chunk state: {fields['state']!r}")
    fields["updated_at"] = _now_iso()
    conn = storage._get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [recording_id, chunk_seq, pipeline_version]
    cursor = conn.execute(
        f"UPDATE chunk_progress SET {sets} "
        "WHERE recording_id = ? AND chunk_seq = ? AND pipeline_version = ?",
        values,
    )
    if cursor.rowcount == 0:
        raise KeyError(
            f"Chunk ({recording_id}, {chunk_seq}, v{pipeline_version}) not found"
        )
    conn.commit()
    return get_chunk(recording_id, chunk_seq, pipeline_version)  # type: ignore[return-value]


def list_chunks_for_recording(
    recording_id: str, pipeline_version: Optional[int] = None
) -> list[dict[str, Any]]:
    """Return all chunks for a recording, ordered by sequence.

    If `pipeline_version` is None, the current version is used (read from
    recording_pipeline_state).
    """
    conn = storage._get_conn()
    if pipeline_version is None:
        state = get_state(recording_id)
        pipeline_version = state["pipeline_version"] if state else 1
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM chunk_progress "
        "WHERE recording_id = ? AND pipeline_version = ? "
        "ORDER BY chunk_seq",
        (recording_id, pipeline_version),
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def list_chunks_in_state(
    state: str, recording_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return chunks in the requested state (`queued`, `processing`, etc.)."""
    if state not in VALID_CHUNK_STATES:
        raise ValueError(f"Invalid chunk state: {state!r}")
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    if recording_id is None:
        rows = conn.execute(
            "SELECT * FROM chunk_progress WHERE state = ? ORDER BY updated_at",
            (state,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM chunk_progress "
            "WHERE state = ? AND recording_id = ? ORDER BY chunk_seq",
            (state, recording_id),
        ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def find_by_sha(recording_id: str, sha256: str, pipeline_version: int = 1) -> Optional[dict[str, Any]]:
    """Lookup by content hash. Idempotency check during chunk ingestion."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM chunk_progress "
        "WHERE recording_id = ? AND sha256 = ? AND pipeline_version = ?",
        (recording_id, sha256, pipeline_version),
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None
