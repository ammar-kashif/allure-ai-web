"""Synthetic eval-query generator.

Strategy:
    1. Sample N segments + N outcomes from completed recordings (stratified
       so we don't over-represent one giant meeting).
    2. For each sample, build a question deterministically if a clear shape
       exists (literal $ amount → "When did we discuss <amount>?"; outcome
       title → "What was the <type> about <X>?").
    3. If a hosted LLM is configured, optionally rewrite questions to sound
       more natural. Skip in CI / no-key setups.
    4. Store each as an eval_query row with `expected_sources` = the
       recording_id (+ segment_index for transcript queries) it came from.

Run via the /eval/generate endpoint or `python -m ghost.eval.generator`.
"""

import logging
import random
import sqlite3
from typing import Any, Optional

import storage
from ghost.eval import store as eval_store

logger = logging.getLogger(__name__)


def _sample_segments(n: int = 25) -> list[dict[str, Any]]:
    """Stratified-by-recording sample of substantive segments."""
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    # Stratify: at most 3 segments per recording.
    rows = conn.execute(
        """
        SELECT recording_id, segment_index, speaker, text, start_seconds
        FROM segments
        WHERE length(text) > 40
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (n * 4,),
    ).fetchall()
    conn.row_factory = None
    out: list[dict[str, Any]] = []
    per_rec: dict[str, int] = {}
    for r in rows:
        rid = r["recording_id"]
        if per_rec.get(rid, 0) >= 3:
            continue
        per_rec[rid] = per_rec.get(rid, 0) + 1
        out.append(dict(r))
        if len(out) >= n:
            break
    return out


def _sample_outcomes(n: int = 25) -> list[dict[str, Any]]:
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT j.id AS recording_id, j.outcomes AS outcomes_json,
               json_extract(j.result, '$.meeting_title') AS meeting_title
        FROM jobs j
        WHERE j.status = 'completed'
          AND j.outcomes IS NOT NULL
          AND j.outcomes != '[]'
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (n * 2,),
    ).fetchall()
    conn.row_factory = None
    import json as _json
    out: list[dict[str, Any]] = []
    for r in rows:
        outcomes = _json.loads(r["outcomes_json"] or "[]")
        if not outcomes:
            continue
        o = random.choice(outcomes)
        out.append({
            "recording_id": r["recording_id"],
            "meeting_title": r["meeting_title"],
            "outcome": o,
        })
        if len(out) >= n:
            break
    return out


def _q_for_segment(seg: dict[str, Any]) -> Optional[dict[str, Any]]:
    text = (seg.get("text") or "").strip()
    if not text:
        return None
    # Money mention -> "when did we discuss" query.
    import re
    money_match = re.search(r"\$\s?[\d,]+(?:\.\d{1,2})?", text)
    if money_match:
        amount = money_match.group(0)
        return {
            "question": f"When did we discuss {amount}?",
            "kind": "lookup_money",
            "expected_sources": [{
                "source_type": "segment",
                "recording_id": seg["recording_id"],
                "segment_index": seg["segment_index"],
            }],
        }
    # Speaker-bound query.
    speaker = seg.get("speaker")
    if speaker and speaker not in (None, "", "Unknown"):
        # Use first two distinctive nouns from text as topic.
        topic_words = [w for w in re.findall(r"[A-Z][a-z]{3,}", text)][:2]
        if topic_words:
            topic = " ".join(topic_words)
            return {
                "question": f"What did {speaker} say about {topic}?",
                "kind": "lookup_speaker_topic",
                "expected_sources": [{
                    "source_type": "segment",
                    "recording_id": seg["recording_id"],
                    "segment_index": seg["segment_index"],
                }],
            }
    return None


def _q_for_outcome(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    o = item.get("outcome") or {}
    otype = o.get("type")
    title = (o.get("title") or "").strip()
    if not (otype and title):
        return None
    # "What was the decision about X?"
    short = " ".join(title.split()[:5])
    return {
        "question": f"What was the {otype} about {short}?",
        "kind": "lookup_outcome",
        "expected_sources": [{
            "source_type": "outcome",
            "recording_id": item["recording_id"],
            "outcome_id": o.get("id"),
        }],
    }


def generate(n_target: int = 50) -> dict[str, Any]:
    """Generate up to n_target eval queries. Idempotent only in the sense
    that you can call it repeatedly; new rows accumulate."""
    n_each = max(1, n_target // 2)
    seg_samples = _sample_segments(n_each)
    out_samples = _sample_outcomes(n_each)
    created = 0
    skipped = 0
    for s in seg_samples:
        q = _q_for_segment(s)
        if q is None:
            skipped += 1
            continue
        eval_store.add_query(q["question"], q["kind"], q["expected_sources"])
        created += 1
    for o in out_samples:
        q = _q_for_outcome(o)
        if q is None:
            skipped += 1
            continue
        eval_store.add_query(q["question"], q["kind"], q["expected_sources"])
        created += 1
    return {
        "created": created,
        "skipped": skipped,
        "sampled_segments": len(seg_samples),
        "sampled_outcomes": len(out_samples),
    }
