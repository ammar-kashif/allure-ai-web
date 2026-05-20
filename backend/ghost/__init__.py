"""Ghost: multi-agent retrieval over project memory.

Layout:
    retrieval/   -- VectorRetriever, FTSRetriever, StructuredRetriever, HybridRetriever
    embeddings   -- bge-small-en-v1.5 wrapper + sqlite-vec storage
    llm          -- hosted LLM factory (Anthropic / OpenAI / OpenAI-compatible)
    tools        -- agent-facing tool implementations
    agent        -- single-agent tool-use loop + sub-agent escalation
    triage       -- pre-loop classifier (scope, intent)

Phase 4 ships retrieval + embeddings. Subsequent phases add llm/tools/agent.
"""
