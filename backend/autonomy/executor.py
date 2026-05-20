"""Apply autonomy actions: deterministic gates → frontend task writes →
audit rows. Never raises; gate failures write `skipped_*` actions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from extraction import format_backlink
from observability import log_event

from . import store as autonomy_store
from .verifier import verify_proposal

logger = logging.getLogger(__name__)

DUPLICATE_SIM_THRESHOLD = 0.85


def _embed_safely(texts: list[str]):
    """Wrapper around ghost.embeddings.embed_texts that swallows errors
    (model load failure shouldn't crash the autonomy pass)."""
    try:
        from ghost.embeddings import embed_texts

        return embed_texts(texts)
    except Exception:
        logger.exception("embed_texts failed in autonomy gates")
        return None


def _cosine_max(query_vec, matrix) -> float:
    import numpy as np

    if matrix is None or len(matrix) == 0:
        return 0.0
    # query_vec is normalized; matrix rows are normalized; cosine = dot
    sims = matrix @ query_vec
    return float(np.max(sims))


def _gate_check(
    proposal: dict[str, Any],
    open_tasks: list[dict[str, Any]],
    segments_len: int,
) -> tuple[bool, str]:
    """Return (passed, reason)."""
    title = (proposal.get("title") or "").strip()
    owner = (proposal.get("owner_name") or "").strip()
    verb = (proposal.get("verb_phrase") or "").strip()
    idx = proposal.get("source_segment_index")
    dup_id = proposal.get("duplicate_of_task_id")

    if not title:
        return False, "missing title"
    if not owner:
        return False, "missing owner"
    if not verb:
        return False, "missing verb phrase"
    if not isinstance(idx, int) or not (0 <= idx < segments_len):
        return False, "source_segment_index out of range"
    if dup_id:
        return False, f"detector flagged as duplicate of {dup_id}"
    return True, "ok"


def _dedupe_check(
    proposal_title: str,
    existing_titles: list[str],
) -> tuple[bool, Optional[float]]:
    """Returns (is_duplicate, max_similarity_or_None)."""
    if not existing_titles:
        return False, None
    matrix = _embed_safely(existing_titles)
    if matrix is None:
        return False, None
    proposal_matrix = _embed_safely([proposal_title])
    if proposal_matrix is None or len(proposal_matrix) == 0:
        return False, None
    sim = _cosine_max(proposal_matrix[0], matrix)
    return sim >= DUPLICATE_SIM_THRESHOLD, sim


def apply(
    run_id: str,
    recording_id: str,
    detect_payload: dict[str, Any],
    context: dict[str, Any],
    llm: Any,
) -> dict[str, Any]:
    """Walk task_matches + proposed_new_tasks, run verifier on proposals,
    apply gates, write tasks + audit rows. Returns aggregate counts +
    tokens used by the verifier sub-pass.
    """
    from frontend_sync import create_task_with_audit_link

    segments = context.get("segments", []) or []
    open_tasks = context.get("open_tasks", []) or []
    existing_titles = [t.get("title", "") for t in open_tasks if t.get("title")]
    open_task_ids = {t["id"] for t in open_tasks}
    job = context.get("job") or {}
    original_filename = job.get("original_filename", "Recording")

    verify_tokens_in = 0
    verify_tokens_out = 0
    verify_cost = 0.0

    # 1) task_matches — low-risk audit rows, no verifier, no mutation.
    for m in detect_payload.get("task_matches") or []:
        task_id = m.get("task_id")
        action = m.get("action") or "none"
        evidence = m.get("evidence_segments") or []
        reason = m.get("reason", "")
        if action == "none":
            continue
        if task_id not in open_task_ids:
            # Detector hallucinated a task id — skip silently rather than
            # creating noise. Audit it as a gate skip.
            autonomy_store.add_action(
                run_id,
                recording_id,
                kind="skipped_gate",
                reason=f"task_match referenced unknown task_id={task_id}",
                detector_payload=m,
            )
            continue
        kind_map = {
            "discussed": "task_discussed",
            "appears_done": "task_appears_done",
            "appears_blocked": "task_appears_blocked",
        }
        kind = kind_map.get(action)
        if kind is None:
            continue
        seg_idx = evidence[0] if evidence else None
        speaker = None
        if isinstance(seg_idx, int) and 0 <= seg_idx < len(segments):
            speaker = segments[seg_idx].get("speaker")
        autonomy_store.add_action(
            run_id,
            recording_id,
            kind=kind,
            target_task_id=task_id,
            segment_index=seg_idx if isinstance(seg_idx, int) else None,
            speaker=speaker,
            reason=reason,
            detector_payload=m,
        )

    # 2) proposed_new_tasks — verifier + gates + create + audit.
    for proposal in detect_payload.get("proposed_new_tasks") or []:
        passed, gate_reason = _gate_check(proposal, open_tasks, len(segments))
        if not passed:
            autonomy_store.add_action(
                run_id,
                recording_id,
                kind="skipped_gate",
                reason=gate_reason,
                detector_payload=proposal,
            )
            continue

        # Dedupe via embeddings.
        is_dup, sim = _dedupe_check(proposal["title"], existing_titles)
        if is_dup:
            autonomy_store.add_action(
                run_id,
                recording_id,
                kind="skipped_duplicate",
                reason=f"cosine_sim={sim:.3f} >= {DUPLICATE_SIM_THRESHOLD}",
                detector_payload=proposal,
            )
            continue

        # Verifier critic.
        verdict = verify_proposal(proposal, segments, open_tasks, llm)
        verify_tokens_in += verdict["tokens_in"]
        verify_tokens_out += verdict["tokens_out"]
        verify_cost += verdict["cost_usd"]

        if verdict["vote"] != "ship":
            autonomy_store.add_action(
                run_id,
                recording_id,
                kind="skipped_verifier",
                reason="verifier voted skip",
                verifier_reason=verdict["reason"],
                detector_payload=proposal,
            )
            continue

        # All gates passed — create the task and the matching audit row.
        seg_idx = int(proposal["source_segment_index"])
        speaker = segments[seg_idx].get("speaker", "Unknown") if 0 <= seg_idx < len(segments) else "Unknown"
        timestamp = float(segments[seg_idx].get("start", 0.0)) if 0 <= seg_idx < len(segments) else 0.0
        backlink = format_backlink(original_filename, timestamp, speaker)

        action = autonomy_store.add_action(
            run_id,
            recording_id,
            kind="task_created",
            segment_index=seg_idx,
            speaker=speaker,
            reason=proposal.get("reason", ""),
            verifier_reason=verdict["reason"],
            detector_payload=proposal,
        )

        try:
            task_row = create_task_with_audit_link(
                recording_id=recording_id,
                title=proposal["title"],
                assignee=proposal["owner_name"],
                detail=proposal.get("verb_phrase", ""),
                backlink=backlink,
                autonomy_action_id=action["id"],
                autonomy_run_id=run_id,
            )
            if task_row and task_row.get("id"):
                # Save the frontend task id on the audit row for undo.
                import storage as _storage

                conn = _storage._get_conn()
                conn.execute(
                    "UPDATE autonomy_actions SET target_task_id = ? WHERE id = ?",
                    (task_row["id"], action["id"]),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("create_task_with_audit_link failed for %s", action["id"])
            # Mark the action as a gate-skip so the run summary is consistent.
            autonomy_store.mark_action_reversed(action["id"])
            autonomy_store.add_action(
                run_id,
                recording_id,
                kind="skipped_gate",
                reason=f"task insert failed: {exc}",
                detector_payload=proposal,
            )

    log_event(
        category="autonomy",
        event="autonomy.execute",
        status="done",
        message="Autonomy actions applied",
        recording_id=recording_id,
        metadata={"run_id": run_id},
    )
    return {
        "verify_tokens_in": verify_tokens_in,
        "verify_tokens_out": verify_tokens_out,
        "verify_cost_usd": round(verify_cost, 6),
    }
