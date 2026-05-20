"""Aggregate per-step latency from the `logs` table.

`observability.step_timer` writes a `step.done` row per stage with
`duration_ms` populated. This module reads those rows and computes
p50/p95/p99/count per step name over a sliding window, exposed via the
`/metrics` endpoint. Used by Phase 7 nightly evals to enforce regression
thresholds.
"""

import sqlite3
from typing import Any

import storage


def percentile(values: list[int], p: float) -> int:
    """Nearest-rank percentile (0 <= p <= 100). Returns 0 if empty."""
    if not values:
        return 0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    s = sorted(values)
    k = max(0, int(round((p / 100.0) * len(s))) - 1)
    return s[k]


def step_latencies(
    *,
    since_iso: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Aggregate latency stats per `(category, event)`.

    Filters to rows with `status='done'` and a `duration_ms` value. If
    `since_iso` is None the full table is scanned -- callers should always
    pass a window in production.
    """
    conn = storage._get_conn()
    conn.row_factory = sqlite3.Row
    where = ["status = 'done'", "duration_ms IS NOT NULL"]
    params: list[Any] = []
    if since_iso:
        where.append("created_at >= ?")
        params.append(since_iso)
    if category:
        where.append("category = ?")
        params.append(category)
    sql = (
        "SELECT category, event, duration_ms FROM logs WHERE "
        + " AND ".join(where)
        + " ORDER BY category, event"
    )
    rows = conn.execute(sql, params).fetchall()
    conn.row_factory = None

    bucket: dict[tuple[str, str], list[int]] = {}
    for r in rows:
        bucket.setdefault((r["category"], r["event"]), []).append(int(r["duration_ms"]))

    out: list[dict[str, Any]] = []
    for (cat, ev), values in bucket.items():
        out.append(
            {
                "category": cat,
                "event": ev,
                "count": len(values),
                "p50_ms": percentile(values, 50),
                "p95_ms": percentile(values, 95),
                "p99_ms": percentile(values, 99),
                "max_ms": max(values),
                "min_ms": min(values),
            }
        )
    out.sort(key=lambda d: d["p95_ms"], reverse=True)
    return out


def pipeline_summary(since_iso: str | None = None) -> dict[str, Any]:
    """High-level rollup. Useful for dashboards and CI assertions."""
    rows = step_latencies(since_iso=since_iso)
    by_step = {f"{r['category']}.{r['event']}": r for r in rows}
    return {"steps": rows, "by_step": by_step, "total_steps": len(rows)}
