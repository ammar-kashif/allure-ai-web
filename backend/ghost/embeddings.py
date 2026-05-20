"""Embedding model + sqlite-vec storage.

Model: bge-small-en-v1.5 (384 dim, English-only, runs CPU). Locked per
plan -- swap is a one-line change here but the schema dimension would
need to change too.

sqlite-vec is loaded as a runtime extension into the existing SQLite
connection -- no separate database. Three virtual tables hold embeddings
for segments / attachments / outcomes. A side mapping table links each
vec0 rowid back to its source row.
"""

import logging
import os
import threading
from typing import Iterable, Optional

import numpy as np

import storage

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
EMBEDDING_MODEL_NAME = os.environ.get("GHOST_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

_model = None
_model_lock = threading.Lock()


def get_model():
    """Lazy-load the sentence-transformers model once. Thread-safe."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s", EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return (N, EMBEDDING_DIM) float32 array. Normalized for cosine
    similarity (sqlite-vec's distance defaults work on normalized vecs).
    """
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    model = get_model()
    arr = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return arr.astype(np.float32, copy=False)


def init() -> None:
    """Load sqlite-vec into the shared connection and create vec tables.

    Falls back to creating regular SQLite tables if sqlite-vec is not
    available -- callers (VectorRetriever) detect this and skip vector
    queries gracefully. FTS + structured retrieval still work.
    """
    conn = storage._get_conn()
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception as exc:
        logger.warning(
            "sqlite-vec not available (%s); vector search disabled. "
            "FTS + structured retrieval continue to work.",
            exc,
        )
        # Still create the mapping tables so the rest of the code can
        # write/read deterministically -- vector queries will return [].
        _create_mapping_tables(conn)
        return

    # vec0 virtual tables.
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS segment_vecs USING vec0(embedding float[{EMBEDDING_DIM}])"
    )
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS attachment_vecs USING vec0(embedding float[{EMBEDDING_DIM}])"
    )
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS outcome_vecs USING vec0(embedding float[{EMBEDDING_DIM}])"
    )
    _create_mapping_tables(conn)
    conn.commit()


def _create_mapping_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS segment_vec_map (
            rowid           INTEGER PRIMARY KEY,
            recording_id    TEXT NOT NULL,
            segment_index   INTEGER NOT NULL,
            UNIQUE(recording_id, segment_index)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attachment_vec_map (
            rowid           INTEGER PRIMARY KEY,
            attachment_id   TEXT NOT NULL UNIQUE,
            recording_id    TEXT NOT NULL,
            chunk_index     INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outcome_vec_map (
            rowid           INTEGER PRIMARY KEY,
            outcome_id      TEXT NOT NULL UNIQUE,
            recording_id    TEXT NOT NULL
        )
        """
    )


def vec_search_supported() -> bool:
    """Probe whether sqlite-vec is loaded successfully."""
    conn = storage._get_conn()
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE name = 'segment_vecs'").fetchall()
        return len(rows) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def upsert_segment_embedding(recording_id: str, segment_index: int, embedding: np.ndarray) -> None:
    """Insert or replace the embedding for one segment."""
    conn = storage._get_conn()
    if not vec_search_supported():
        return
    row = conn.execute(
        "SELECT rowid FROM segment_vec_map WHERE recording_id = ? AND segment_index = ?",
        (recording_id, segment_index),
    ).fetchone()
    if row:
        rowid = row[0]
        conn.execute("DELETE FROM segment_vecs WHERE rowid = ?", (rowid,))
        conn.execute(
            "INSERT INTO segment_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.astype(np.float32).tobytes()),
        )
    else:
        cur = conn.execute(
            "INSERT INTO segment_vec_map(recording_id, segment_index) VALUES (?, ?)",
            (recording_id, segment_index),
        )
        rowid = cur.lastrowid
        conn.execute(
            "INSERT INTO segment_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.astype(np.float32).tobytes()),
        )
    conn.commit()


def upsert_outcome_embedding(outcome_id: str, recording_id: str, embedding: np.ndarray) -> None:
    conn = storage._get_conn()
    if not vec_search_supported():
        return
    row = conn.execute(
        "SELECT rowid FROM outcome_vec_map WHERE outcome_id = ?",
        (outcome_id,),
    ).fetchone()
    if row:
        rowid = row[0]
        conn.execute("DELETE FROM outcome_vecs WHERE rowid = ?", (rowid,))
        conn.execute(
            "INSERT INTO outcome_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.astype(np.float32).tobytes()),
        )
    else:
        cur = conn.execute(
            "INSERT INTO outcome_vec_map(outcome_id, recording_id) VALUES (?, ?)",
            (outcome_id, recording_id),
        )
        rowid = cur.lastrowid
        conn.execute(
            "INSERT INTO outcome_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.astype(np.float32).tobytes()),
        )
    conn.commit()


def upsert_attachment_embedding(
    attachment_id: str, recording_id: str, chunk_index: int, embedding: np.ndarray
) -> None:
    conn = storage._get_conn()
    if not vec_search_supported():
        return
    row = conn.execute(
        "SELECT rowid FROM attachment_vec_map WHERE attachment_id = ? AND chunk_index = ?",
        (attachment_id, chunk_index),
    ).fetchone()
    if row:
        rowid = row[0]
        conn.execute("DELETE FROM attachment_vecs WHERE rowid = ?", (rowid,))
        conn.execute(
            "INSERT INTO attachment_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.astype(np.float32).tobytes()),
        )
    else:
        cur = conn.execute(
            "INSERT INTO attachment_vec_map(attachment_id, recording_id, chunk_index) "
            "VALUES (?, ?, ?)",
            (attachment_id, recording_id, chunk_index),
        )
        rowid = cur.lastrowid
        conn.execute(
            "INSERT INTO attachment_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding.astype(np.float32).tobytes()),
        )
    conn.commit()


def delete_segment_embeddings(recording_id: str) -> int:
    """Used when re-embedding a recording. Cascades through vec0 + map."""
    conn = storage._get_conn()
    if not vec_search_supported():
        return 0
    rows = conn.execute(
        "SELECT rowid FROM segment_vec_map WHERE recording_id = ?",
        (recording_id,),
    ).fetchall()
    n = 0
    for (rowid,) in rows:
        conn.execute("DELETE FROM segment_vecs WHERE rowid = ?", (rowid,))
        n += 1
    conn.execute("DELETE FROM segment_vec_map WHERE recording_id = ?", (recording_id,))
    conn.commit()
    return n


def embed_and_index_recording(recording_id: str) -> int:
    """Compute + persist embeddings for every segment of a recording.

    Returns the number of segments embedded. Idempotent -- prior embeddings
    are wiped first.

    Encoding: "{speaker}: {text}" so vector retrieval picks up speaker
    semantics (queries like "what did Jason say about X" match the right
    segments even when 'Jason' never appears in the transcript text).
    """
    from segments_store import list_segments

    segments = list_segments(recording_id)
    if not segments:
        return 0
    delete_segment_embeddings(recording_id)
    texts = []
    for s in segments:
        speaker = (s.get("speaker") or "").strip()
        body = s.get("text", "")
        texts.append(f"{speaker}: {body}" if speaker else body)
    matrix = embed_texts(texts)
    for s, vec in zip(segments, matrix):
        upsert_segment_embedding(recording_id, s["segment_index"], vec)
    return len(segments)


def embed_outcomes(recording_id: str, outcomes: Iterable[dict]) -> int:
    n = 0
    docs = list(outcomes)
    if not docs:
        return 0
    texts = [f"{d.get('title','')}: {d.get('detail','')}" for d in docs]
    matrix = embed_texts(texts)
    for d, vec in zip(docs, matrix):
        oid = d.get("id")
        if not oid:
            continue
        upsert_outcome_embedding(oid, recording_id, vec)
        n += 1
    return n


def embed_attachment(attachment_id: str, recording_id: str, text: str, *, chunk_chars: int = 2000) -> int:
    """Chunk an attachment's text and embed each chunk.

    Simple character-based chunking with no overlap. Good enough for v1;
    semantic chunking is a future improvement.
    """
    if not text or not text.strip():
        return 0
    chunks = [text[i:i + chunk_chars] for i in range(0, len(text), chunk_chars)]
    matrix = embed_texts(chunks)
    for i, vec in enumerate(matrix):
        upsert_attachment_embedding(attachment_id, recording_id, i, vec)
    return len(chunks)
