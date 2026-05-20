"""SQLite-backed entity + mention store.

Includes FTS5 virtual tables for transcripts / attachments / outcomes,
populated by triggers so app code never has to remember to update them
(this is the SQLite stored-procedure equivalent).

Resolution order when inserting a mention's entity:
    1. exact canonical-name match (case-insensitive)
    2. alias match (JSON array lookup)
    3. fuzzy match via rapidfuzz at >= ALIAS_FUZZ_THRESHOLD
    4. otherwise: create a new entity row
"""

import datetime as dt
import json
import logging
import sqlite3
import uuid
from typing import Any, Iterable, Optional

import storage

logger = logging.getLogger(__name__)

VALID_KINDS = {"person", "project", "money", "date", "deliverable", "org", "document"}
ALIAS_FUZZ_THRESHOLD = 92  # rapidfuzz ratio out of 100


def init() -> None:
    """Create entities, mentions, FTS tables, triggers, and views."""
    conn = storage._get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entities (
            id              TEXT PRIMARY KEY,
            kind            TEXT NOT NULL,
            canonical_name  TEXT NOT NULL,
            aliases_json    TEXT NOT NULL DEFAULT '[]',
            metadata_json   TEXT NOT NULL DEFAULT '{}',
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            last_seen_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            mention_count   INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entities_kind_name "
        "ON entities(kind, canonical_name COLLATE NOCASE)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entities_last_seen ON entities(last_seen_at DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_mentions (
            id              TEXT PRIMARY KEY,
            entity_id       TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            source_type     TEXT NOT NULL,
            source_id       TEXT NOT NULL,
            recording_id    TEXT,
            project_id      TEXT,
            timestamp       REAL,
            speaker         TEXT,
            confidence      REAL NOT NULL DEFAULT 1.0,
            snippet         TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentions_entity_recency "
        "ON entity_mentions(entity_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentions_entity_source "
        "ON entity_mentions(entity_id, source_type, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentions_recording ON entity_mentions(recording_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentions_project_recency "
        "ON entity_mentions(project_id, created_at DESC)"
    )

    # FTS5 tables -- segments / attachments / outcomes.
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
            recording_id UNINDEXED,
            segment_index UNINDEXED,
            speaker,
            text,
            timestamp UNINDEXED,
            tokenize = 'porter unicode61'
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS attachments_fts USING fts5(
            attachment_id UNINDEXED,
            recording_id UNINDEXED,
            filename,
            text,
            tokenize = 'porter unicode61'
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS outcomes_fts USING fts5(
            outcome_id UNINDEXED,
            recording_id UNINDEXED,
            type,
            title,
            detail,
            tokenize = 'porter unicode61'
        )
        """
    )

    # Trigger: keep mention_count honest when mentions are deleted (e.g.,
    # entitize re-runs first deletes mentions for the recording before
    # re-inserting them). Without this the count drifts upward.
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS entity_mentions_after_delete
        AFTER DELETE ON entity_mentions
        BEGIN
            UPDATE entities
            SET mention_count = MAX(0, mention_count - 1)
            WHERE id = OLD.entity_id;
        END
        """
    )

    # Triggers: segments → segments_fts.
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS segments_to_fts_insert
        AFTER INSERT ON segments
        BEGIN
            INSERT INTO segments_fts(recording_id, segment_index, speaker, text, timestamp)
            VALUES (NEW.recording_id, NEW.segment_index, NEW.speaker, NEW.text, NEW.start_seconds);
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS segments_to_fts_delete
        AFTER DELETE ON segments
        BEGIN
            DELETE FROM segments_fts
            WHERE recording_id = OLD.recording_id AND segment_index = OLD.segment_index;
        END
        """
    )

    # Triggers: attachments → attachments_fts (text only when present).
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS attachments_to_fts_insert
        AFTER INSERT ON attachments
        BEGIN
            INSERT INTO attachments_fts(attachment_id, recording_id, filename, text)
            VALUES (NEW.id, NEW.recording_id, NEW.filename, NEW.extracted_text);
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS attachments_to_fts_delete
        AFTER DELETE ON attachments
        BEGIN
            DELETE FROM attachments_fts WHERE attachment_id = OLD.id;
        END
        """
    )

    # Outcomes live inside jobs.outcomes JSON today. The entitize pass writes
    # outcomes into outcomes_fts directly (no separate outcomes table yet).
    # We expose helpers below.

    # Views -- the "stored procedures" for common Ghost lookups.
    conn.execute(
        """
        CREATE VIEW IF NOT EXISTS v_recent_activity_by_entity AS
        SELECT
            em.entity_id,
            em.source_type,
            em.source_id,
            em.recording_id,
            em.project_id,
            em.timestamp,
            em.speaker,
            em.snippet,
            COALESCE(j.original_filename, '') AS recording_title,
            em.created_at AS mention_created_at
        FROM entity_mentions em
        LEFT JOIN jobs j ON j.id = em.recording_id
        """
    )
    conn.execute(
        """
        CREATE VIEW IF NOT EXISTS v_entity_summary AS
        SELECT
            e.id,
            e.kind,
            e.canonical_name,
            e.mention_count,
            e.last_seen_at,
            (SELECT COUNT(DISTINCT recording_id) FROM entity_mentions WHERE entity_id = e.id) AS recordings_mentioned_in
        FROM entities e
        """
    )
    conn.execute(
        """
        CREATE VIEW IF NOT EXISTS v_recording_summary AS
        SELECT
            j.id AS recording_id,
            j.original_filename AS title,
            json_extract(j.result, '$.meeting_title') AS meeting_title,
            json_extract(j.result, '$.meeting_description') AS description,
            json_extract(j.result, '$.duration') AS duration,
            (SELECT COUNT(*) FROM entity_mentions WHERE recording_id = j.id) AS entity_count
        FROM jobs j
        WHERE j.status = 'completed'
        """
    )
    conn.commit()


def _now_iso() -> str:
    """Match SQLite's strftime('%Y-%m-%dT%H:%M:%fZ', 'now') format
    (millisecond precision). Mixing this with microsecond timestamps would
    break ISO-8601 string ordering against rows populated by SQLite defaults.
    """
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------


def find_by_exact_name(name: str, kind: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM entities WHERE kind = ? AND canonical_name = ? COLLATE NOCASE",
        (kind, name),
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def find_by_alias(name: str, kind: str) -> Optional[dict[str, Any]]:
    """Walk entities of `kind`, return one whose aliases include `name`."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM entities WHERE kind = ?", (kind,)
    ).fetchall()
    conn.row_factory = None
    lname = name.lower()
    for r in rows:
        aliases = json.loads(r["aliases_json"] or "[]")
        if any(a.lower() == lname for a in aliases):
            return dict(r)
    return None


def find_by_fuzzy(
    name: str, kind: str, threshold: int = ALIAS_FUZZ_THRESHOLD
) -> Optional[tuple[dict[str, Any], int]]:
    """Best fuzzy candidate >= threshold, or None. Returns (entity, score)."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed; fuzzy entity matching disabled")
        return None
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM entities WHERE kind = ?", (kind,)
    ).fetchall()
    conn.row_factory = None
    best: Optional[tuple[dict[str, Any], int]] = None
    for r in rows:
        candidates = [r["canonical_name"]] + json.loads(r["aliases_json"] or "[]")
        score = max(int(fuzz.token_set_ratio(name, c)) for c in candidates)
        if score >= threshold and (best is None or score > best[1]):
            best = (dict(r), score)
    return best


def create_entity(
    kind: str, canonical_name: str, aliases: Iterable[str] = ()
) -> dict[str, Any]:
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown entity kind: {kind!r}")
    entity_id = str(uuid.uuid4())
    aliases_json = json.dumps([a for a in aliases if a and a.lower() != canonical_name.lower()])
    conn = storage._get_conn()
    conn.execute(
        "INSERT INTO entities (id, kind, canonical_name, aliases_json) VALUES (?, ?, ?, ?)",
        (entity_id, kind, canonical_name, aliases_json),
    )
    conn.commit()
    return get_entity(entity_id)  # type: ignore[return-value]


def add_alias(entity_id: str, alias: str) -> None:
    conn = storage._get_conn()
    row = conn.execute(
        "SELECT aliases_json, canonical_name FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"Entity {entity_id} not found")
    aliases = json.loads(row[0] or "[]")
    if alias.lower() == row[1].lower():
        return
    if any(a.lower() == alias.lower() for a in aliases):
        return
    aliases.append(alias)
    conn.execute(
        "UPDATE entities SET aliases_json = ? WHERE id = ?",
        (json.dumps(aliases), entity_id),
    )
    conn.commit()


def resolve_or_create(
    name: str,
    kind: str,
    *,
    aliases: Iterable[str] = (),
    disambiguate_fn=None,
) -> dict[str, Any]:
    """Resolve `name` to an entity row, creating one if necessary.

    `disambiguate_fn`, if provided, is called when a fuzzy match is found
    in the [threshold, 95) gray zone -- it receives (candidate_entity,
    incoming_name, score) and must return True (same entity) or False
    (different entity, create new). In production this is the LLM
    disambiguation pass; tests can pass a deterministic stub.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("entity name is empty")
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown entity kind: {kind!r}")

    hit = find_by_exact_name(name, kind)
    if hit:
        return hit
    hit = find_by_alias(name, kind)
    if hit:
        return hit
    fuzz_hit = find_by_fuzzy(name, kind)
    if fuzz_hit:
        candidate, score = fuzz_hit
        if score >= 95 or disambiguate_fn is None:
            # High-confidence fuzzy match: treat as same entity, add alias.
            add_alias(candidate["id"], name)
            return candidate
        if disambiguate_fn(candidate, name, score):
            add_alias(candidate["id"], name)
            return candidate
        # Disambiguation said different person -- fall through to create.
    return create_entity(kind, canonical_name=name, aliases=aliases)


def get_entity(entity_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def list_entities(
    kind: Optional[str] = None, limit: int = 100
) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    if kind:
        rows = conn.execute(
            "SELECT * FROM entities WHERE kind = ? ORDER BY last_seen_at DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM entities ORDER BY last_seen_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------


def add_mention(
    entity_id: str,
    source_type: str,
    source_id: str,
    *,
    recording_id: Optional[str] = None,
    project_id: Optional[str] = None,
    timestamp: Optional[float] = None,
    speaker: Optional[str] = None,
    confidence: float = 1.0,
    snippet: str = "",
) -> dict[str, Any]:
    mention_id = str(uuid.uuid4())
    now = _now_iso()
    conn = storage._get_conn()
    conn.execute(
        """
        INSERT INTO entity_mentions (
            id, entity_id, source_type, source_id, recording_id,
            project_id, timestamp, speaker, confidence, snippet, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mention_id, entity_id, source_type, source_id, recording_id,
            project_id, timestamp, speaker, confidence, snippet, now,
        ),
    )
    conn.execute(
        "UPDATE entities SET mention_count = mention_count + 1, last_seen_at = ? WHERE id = ?",
        (now, entity_id),
    )
    conn.commit()
    return get_mention(mention_id)  # type: ignore[return-value]


def get_mention(mention_id: str) -> Optional[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM entity_mentions WHERE id = ?", (mention_id,)
    ).fetchone()
    conn.row_factory = None
    return dict(row) if row else None


def list_mentions(
    entity_id: str,
    source_types: Optional[list[str]] = None,
    limit: int = 50,
    since_iso: Optional[str] = None,
) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM entity_mentions WHERE entity_id = ?"
    params: list[Any] = [entity_id]
    if source_types:
        placeholders = ",".join("?" * len(source_types))
        sql += f" AND source_type IN ({placeholders})"
        params.extend(source_types)
    if since_iso:
        sql += " AND created_at >= ?"
        params.append(since_iso)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def list_recent_activity_by_entity(
    entity_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Joined view that returns recording title alongside the mention.
    Powers Ghost's `list_recent_activity` tool.
    """
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM v_recent_activity_by_entity "
        "WHERE entity_id = ? ORDER BY mention_created_at DESC LIMIT ?",
        (entity_id, limit),
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def delete_mentions_for_recording(recording_id: str) -> int:
    conn = storage._get_conn()
    cursor = conn.execute(
        "DELETE FROM entity_mentions WHERE recording_id = ?", (recording_id,)
    )
    conn.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# FTS helpers
# ---------------------------------------------------------------------------


def index_outcomes(recording_id: str, outcomes: list[dict[str, Any]]) -> None:
    """Replace outcomes_fts rows for a recording. Called by the entitize
    job since outcomes are not yet a first-class table."""
    conn = storage._get_conn()
    conn.execute("DELETE FROM outcomes_fts WHERE recording_id = ?", (recording_id,))
    for o in outcomes:
        oid = o.get("id") or str(uuid.uuid4())
        conn.execute(
            "INSERT INTO outcomes_fts(outcome_id, recording_id, type, title, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (oid, recording_id, o.get("type", ""), o.get("title", ""), o.get("detail", "")),
        )
    conn.commit()
