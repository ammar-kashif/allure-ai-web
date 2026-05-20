"""Autonomous meeting follow-up pass.

Runs after extraction + entitize. Detects whether the current meeting
references prior tasks in the same project, detects new commitments
that should become trackable tasks, and creates those tasks (with full
audit + undo) via the proposer→critic pattern + deterministic gates.

PRDs are out of scope for this iteration.
"""
