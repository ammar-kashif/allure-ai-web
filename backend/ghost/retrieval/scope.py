"""Query scope: the universe a retriever searches.

`scope.applies(row)` returns True if the candidate row passes the filter.
Used both as a SQL WHERE-clause builder and as a Python predicate when
post-filtering vec0 results.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Scope:
    recording_ids: Optional[list[str]] = None
    project_ids: Optional[list[str]] = None
    since_iso: Optional[str] = None
    until_iso: Optional[str] = None

    def is_global(self) -> bool:
        return not (self.recording_ids or self.project_ids or self.since_iso or self.until_iso)

    def where_clause(self, *, recording_col: str = "recording_id", created_col: Optional[str] = None) -> tuple[str, list[Any]]:
        """Build a SQL WHERE-clause fragment + params.

        Returns ("(<expr>)", [params...]) or ("1=1", []) if global. Caller
        wraps with AND/WHERE as needed.
        """
        conds: list[str] = []
        params: list[Any] = []
        if self.recording_ids:
            placeholders = ",".join("?" * len(self.recording_ids))
            conds.append(f"{recording_col} IN ({placeholders})")
            params.extend(self.recording_ids)
        if self.project_ids:
            placeholders = ",".join("?" * len(self.project_ids))
            # project_id may live on jobs (j.project_id) or directly on the
            # row. The caller specifies via a custom JOIN; we generate the
            # condition using a subselect that's portable.
            conds.append(
                f"{recording_col} IN (SELECT id FROM jobs WHERE project_id IN ({placeholders}))"
            )
            params.extend(self.project_ids)
        if self.since_iso and created_col:
            conds.append(f"{created_col} >= ?")
            params.append(self.since_iso)
        if self.until_iso and created_col:
            conds.append(f"{created_col} <= ?")
            params.append(self.until_iso)
        if not conds:
            return "1=1", []
        return "(" + " AND ".join(conds) + ")", params
