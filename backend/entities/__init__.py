"""Entity index for Ghost retrieval.

Two tables:
    entities         -- canonical person / project / money / date / org / etc.
    entity_mentions  -- per-source-row mention rows

Extracted at ingestion time by `entitize_job` (runs after extract). Resolved
against existing rows via canonical-name → alias → fuzzy match → LLM
disambiguation. The mentions table is the substrate Ghost agent tools
query against; `v_recent_activity_by_entity` joins it to the jobs row so
"latest update on Jason" returns a recency-sorted timeline.
"""
