"""Pre-loop triage: classify question scope + intent so we can gate
the spawn_research_subagents tool.

Deterministic-first: regex-detectable patterns (dollar amounts, dates,
named entities) bias toward `lookup` / single-source intents. LLM
classification only runs when ambiguity remains; for the common case
this is zero LLM calls.
"""

import re
from dataclasses import dataclass
from typing import Literal

Scope = Literal["single_recording", "single_project", "cross_project"]
Intent = Literal["lookup", "aggregation", "synthesis", "navigation"]


@dataclass
class TriageResult:
    scope: Scope
    intent: Intent
    can_spawn_subagents: bool
    reasoning: str


_AGGREGATION_HINTS = re.compile(
    r"\b(across|summari[sz]e|all|every|each|list|top|most|least|count|average|trend|breakdown|over time)\b",
    re.IGNORECASE,
)
_LOOKUP_HINTS = re.compile(
    r"\b(when|where|who|what did|how much|how many|the latest|most recent|on)\b",
    re.IGNORECASE,
)
_NAVIGATION_HINTS = re.compile(
    r"\b(show me|open|go to|find the recording|which recording|the meeting where)\b",
    re.IGNORECASE,
)
_PROJECT_REF = re.compile(r"\b(project|workstream|in the .* project)\b", re.IGNORECASE)


def triage(question: str, *, scope_hint: Scope = "cross_project") -> TriageResult:
    """Lightweight classifier. `scope_hint` may be passed by the API layer
    when scope is already pinned by the URL (e.g. /recordings/{id}/ask).
    """
    q = question.strip()

    # Intent.
    if _AGGREGATION_HINTS.search(q):
        intent: Intent = "aggregation"
    elif _NAVIGATION_HINTS.search(q):
        intent = "navigation"
    elif _LOOKUP_HINTS.search(q):
        intent = "lookup"
    else:
        intent = "lookup"

    # Scope.
    scope: Scope = scope_hint
    if scope_hint == "cross_project":
        # If the user explicitly mentions a single project name we still treat
        # as cross_project for tool routing; project filtering is done via
        # tool args, not triage. So the only override is collapsing to
        # single_recording when explicit (handled upstream).
        scope = "cross_project"

    can_spawn = (scope == "cross_project") and (intent in ("aggregation", "synthesis"))
    reasoning = f"intent={intent}; scope={scope}; spawn={can_spawn}"
    return TriageResult(scope=scope, intent=intent, can_spawn_subagents=can_spawn, reasoning=reasoning)
