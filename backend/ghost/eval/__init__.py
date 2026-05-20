"""Ghost evaluation: synthetic query generation + nightly eval runner.

The synthetic generator samples segments + outcomes from existing
recordings, asks the LLM to author plausible PM-style questions against
them, and stores each with its known source recording as ground truth.

The runner replays these questions through the Ghost agent and tracks
latency, cost, retrieval recall@k, and citation correctness.
"""
