"""Streaming audio pipeline: per-chunk STT + embedding extraction with
durable progress tracking, plus end-of-meeting diarization + finalization.

The progress store (`progress_store`) is the single source of truth for
"what has been processed" -- a crash mid-chunk never re-processes or skips.
"""
