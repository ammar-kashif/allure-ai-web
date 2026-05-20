"""Hybrid retrieval: vector + FTS + structured queries, fused via RRF."""

from .scope import Scope
from .vector import VectorRetriever
from .fts import FTSRetriever
from .structured import StructuredRetriever
from .hybrid import HybridRetriever, reciprocal_rank_fusion

__all__ = [
    "Scope",
    "VectorRetriever",
    "FTSRetriever",
    "StructuredRetriever",
    "HybridRetriever",
    "reciprocal_rank_fusion",
]
