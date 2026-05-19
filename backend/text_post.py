"""Per-segment punctuation + capitalization restoration.

Moonshine emits unpunctuated lowercase text. We restore both via a small
dedicated punctuation model (Oliver Guhr's fullstop family) plus a
post-hoc capitalization pass. Per-segment processing — segments from
Moonshine are already roughly sentence-shaped (silence-segmented), so
concatenation across segments isn't needed for v1.

The `deepmultilingualpunctuation` package (v1.0.1, last updated 2021) was
written against an older transformers API that used `grouped_entities=False`
— removed in transformers >= 5 in favor of `aggregation_strategy`. We
monkey-patch the wrapper at import time so it works with current
transformers.
"""

import re
from typing import Any

from observability import step_timer


def _patch_deepmultilingualpunctuation() -> None:
    """Replace the wrapper's `__init__` to use modern transformers API."""
    try:
        import deepmultilingualpunctuation.punctuationmodel as _pm
        from transformers import pipeline
        import torch
    except Exception:
        return

    def _new_init(self, model: str = "oliverguhr/fullstop-punctuation-multilang-large") -> None:
        # Pick best available device; CPU fallback otherwise.
        device: Any = -1
        try:
            if torch.cuda.is_available():
                device = 0
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
        except Exception:
            device = -1
        self.pipe = pipeline(
            "ner", model=model, aggregation_strategy="none", device=device
        )

    _pm.PunctuationModel.__init__ = _new_init


_patch_deepmultilingualpunctuation()


_CAP_AFTER_PUNCT = re.compile(r"([.?!])\s+([a-z])")
_STANDALONE_I = re.compile(r"\bi\b")


def restore_capitalization(text: str) -> str:
    """Capitalize the segment's first letter, the first letter after each
    sentence-ending punctuation, and standalone 'i' → 'I'."""
    if not text:
        return text
    text = text[:1].upper() + text[1:]
    text = _CAP_AFTER_PUNCT.sub(lambda m: f"{m.group(1)} {m.group(2).upper()}", text)
    text = _STANDALONE_I.sub("I", text)
    return text


def punctuate_segments(
    segments: list[dict[str, Any]], punctuator: object
) -> list[dict[str, Any]]:
    """Mutate `segments` in place: restore punctuation + capitalization on each
    non-empty `text` field. Returns the same list for chainability."""
    if not segments or punctuator is None:
        return segments

    with step_timer("punctuate", n_segments=len(segments)):
        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            try:
                punctuated = punctuator.restore_punctuation(text)
                if not isinstance(punctuated, str):
                    punctuated = text
            except Exception:
                # Fail open — keep original text on per-segment error.
                punctuated = text
            try:
                seg["text"] = restore_capitalization(punctuated)
            except Exception:
                seg["text"] = punctuated

    return segments
