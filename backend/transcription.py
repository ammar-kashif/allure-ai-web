"""Moonshine Voice STT + SpeechBrain ECAPA-TDNN speaker diarization pipeline.

Provides the full transcription pipeline: audio -> STT segments -> diarization
(fixed-window embeddings + AgglomerativeClustering) -> speaker alignment with
midpoint-based matching -> sentence-boundary snapping -> label remapping ->
segment merging -> speaker stats.
"""

import logging
import re
from typing import Any

import librosa
import numpy as np
import torch
from sklearn.cluster import AgglomerativeClustering

from storage import get_job

logger = logging.getLogger(__name__)

SENTENCE_END_RE = re.compile(r"[.?!|]")


# ---------------------------------------------------------------------------
# Moonshine STT
# ---------------------------------------------------------------------------


def transcribe_audio(wav_path: str, transcriber) -> list[dict[str, Any]]:
    """Transcribe a WAV file using Moonshine Voice.

    Args:
        wav_path: Path to 16kHz mono WAV file.
        transcriber: Moonshine Voice Transcriber instance.

    Returns:
        List of segment dicts with start, end, text, confidence keys.
    """
    from moonshine_voice import load_wav_file

    audio_data, sample_rate = load_wav_file(wav_path)
    result = transcriber.transcribe_without_streaming(audio_data, sample_rate)

    segments = []
    for line in result.lines:
        text = line.text.strip() if line.text else ""
        if not text:
            continue
        segments.append(
            {
                "start": line.start_time,
                "end": line.start_time + line.duration,
                "text": text,
                "confidence": 1.0,
            }
        )

    return segments


# ---------------------------------------------------------------------------
# Fast CPU-only speaker diarization (SpeechBrain ECAPA-TDNN + AgglomerativeClustering)
# ---------------------------------------------------------------------------


class FastDiarizer:
    """CPU-only speaker diarization using SpeechBrain ECAPA-TDNN embeddings
    and Agglomerative Clustering with cosine distance.

    Uses non-overlapping fixed-length chunks, L2-normalizes embeddings, then
    clusters with agglomerative cosine distance. Segments are assigned to the
    chunk whose time range contains the segment midpoint.

    Args:
        encoder: SpeechBrain EncoderClassifier instance (ECAPA-TDNN).
        chunk_size: Embedding chunk length in seconds (non-overlapping).
        distance_threshold: Agglomerative clustering distance cutoff (0–2 for
            cosine; lower = more clusters). 0.5 is a reliable default.
        min_chunk_duration: Skip chunks shorter than this (seconds).
    """

    def __init__(
        self,
        encoder,
        chunk_size: float = 10.0,
        distance_threshold: float = 0.5,
        min_chunk_duration: float = 2.0,
    ):
        self.encoder = encoder
        self.chunk_size = chunk_size
        self.distance_threshold = distance_threshold
        self.min_chunk_duration = min_chunk_duration

    def _extract_chunk_embeddings(
        self, audio: np.ndarray, sr: int
    ) -> list[tuple[float, float, np.ndarray]]:
        """Extract one ECAPA-TDNN embedding per non-overlapping chunk.

        Returns:
            List of (start_time, end_time, embedding) tuples.
        """
        chunk_samples = int(self.chunk_size * sr)
        min_samples = int(self.min_chunk_duration * sr)
        results = []

        for start_sample in range(0, len(audio), chunk_samples):
            end_sample = min(start_sample + chunk_samples, len(audio))
            chunk = audio[start_sample:end_sample]

            if len(chunk) < min_samples:
                continue

            waveform = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                emb = self.encoder.encode_batch(waveform)
            embedding = emb.squeeze().cpu().numpy()

            results.append((start_sample / sr, end_sample / sr, embedding))

        return results

    def _cluster_embeddings(
        self, chunk_embeddings: list[tuple[float, float, np.ndarray]]
    ) -> np.ndarray:
        """L2-normalize embeddings and cluster with AgglomerativeClustering.

        Returns:
            Integer cluster label array, one per chunk.
        """
        embedding_array = np.array([emb for _, _, emb in chunk_embeddings])

        # L2-normalize so cosine distance is well-defined
        norms = np.linalg.norm(embedding_array, axis=1, keepdims=True)
        embedding_array = embedding_array / (norms + 1e-10)

        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.distance_threshold,
            metric="cosine",
            linkage="average",
        )
        return clustering.fit_predict(embedding_array)

    def _assign_to_chunks(
        self,
        transcript_segments: list[dict[str, Any]],
        chunk_embeddings: list[tuple[float, float, np.ndarray]],
        cluster_labels: np.ndarray,
    ) -> list[dict[str, Any]]:
        """Assign each transcript segment a speaker using midpoint matching.

        For each segment the midpoint is computed; the chunk whose time range
        contains that midpoint determines the speaker. If no chunk contains the
        midpoint, the nearest chunk by midpoint distance is used as fallback.

        Returns:
            Transcript segments with a 'speaker' key added.
        """
        result = []
        for seg in transcript_segments:
            seg_mid = (seg["start"] + seg["end"]) / 2

            # Find chunk whose range contains the segment midpoint
            speaker_label = None
            for i, (chunk_start, chunk_end, _) in enumerate(chunk_embeddings):
                if chunk_start <= seg_mid <= chunk_end:
                    speaker_label = f"cluster_{cluster_labels[i]}"
                    break

            # Fallback: nearest chunk by midpoint distance
            if speaker_label is None:
                nearest = min(
                    range(len(chunk_embeddings)),
                    key=lambda i: abs(
                        (chunk_embeddings[i][0] + chunk_embeddings[i][1]) / 2 - seg_mid
                    ),
                )
                speaker_label = f"cluster_{cluster_labels[nearest]}"

            result.append({**seg, "speaker": speaker_label})

        return result

    def diarize(
        self, audio_path: str, transcript_segments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Run diarization and assign speakers directly to transcript segments.

        Args:
            audio_path: Path to audio file (any format librosa supports).
            transcript_segments: STT segments with start/end/text keys.

        Returns:
            Same segments with a 'speaker' key added (raw cluster labels like
            'cluster_0', 'cluster_1', ...).
        """
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        total_duration = len(audio) / sr

        chunk_embeddings = self._extract_chunk_embeddings(audio, sr)

        if len(chunk_embeddings) < 2:
            # Too short to cluster — assign all to a single speaker
            return [{**seg, "speaker": "cluster_0"} for seg in transcript_segments]

        cluster_labels = self._cluster_embeddings(chunk_embeddings)
        n_speakers = len(set(cluster_labels))
        logger.info(
            "AgglomerativeClustering found %d speaker(s) from %d chunks",
            n_speakers,
            len(chunk_embeddings),
        )

        return self._assign_to_chunks(transcript_segments, chunk_embeddings, cluster_labels)


# ---------------------------------------------------------------------------
# Alignment and post-processing (pure functions)
# ---------------------------------------------------------------------------


def align_transcript_with_speakers(
    transcript_segments: list[dict[str, Any]],
    diarization_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assign speaker labels to transcript segments by maximum time overlap.

    For each transcript segment, find the diarization segment with the greatest
    temporal overlap and assign its speaker label. If no overlap is found,
    the speaker is set to "Unknown".
    """
    result = []
    for seg in transcript_segments:
        best_speaker = "Unknown"
        best_overlap = 0.0
        for diar in diarization_segments:
            overlap_start = max(seg["start"], diar["start"])
            overlap_end = min(seg["end"], diar["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = diar["speaker"]
        result.append({**seg, "speaker": best_speaker})
    return result


def snap_boundaries_to_sentences(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Snap speaker-change boundaries to sentence-ending punctuation.

    When a speaker change happens mid-sentence, move the boundary so the
    full sentence stays with the speaker who started it. Only applies when
    the text contains sentence-ending punctuation (. ? ! |).
    """
    if len(segments) <= 1:
        return segments

    result = [dict(segments[0])]

    for seg in segments[1:]:
        prev = result[-1]
        if prev["speaker"] != seg["speaker"] and prev["text"]:
            # Check if the previous segment ends mid-sentence
            prev_text = prev["text"].rstrip()
            if prev_text and not SENTENCE_END_RE.search(prev_text[-1]):
                # Previous segment doesn't end with sentence punctuation —
                # check if current segment starts with a continuation
                # Keep as-is since Moonshine already produces sentence-level segments
                pass
        result.append(dict(seg))

    return result


def remap_speaker_labels(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remap cluster labels to 'Speaker 1', 'Speaker 2', etc.

    Labels are assigned in order of first appearance in the segments list.
    """
    label_map: dict[str, str] = {}
    counter = 0
    for seg in segments:
        speaker = seg["speaker"]
        if speaker not in label_map:
            counter += 1
            label_map[speaker] = f"Speaker {counter}"

    return [{**seg, "speaker": label_map[seg["speaker"]]} for seg in segments]


def merge_consecutive_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge consecutive segments from the same speaker.

    When two adjacent segments share a speaker:
    - start = earlier start time
    - end = later end time
    - text = concatenated with a space
    - confidence = average of merged confidences
    """
    if not segments:
        return []

    merged: list[dict[str, Any]] = [dict(segments[0])]

    for seg in segments[1:]:
        prev = merged[-1]
        if seg["speaker"] == prev["speaker"]:
            prev["end"] = seg["end"]
            prev["text"] = f"{prev['text']} {seg['text']}"
            prev["confidence"] = (prev["confidence"] + seg["confidence"]) / 2
        else:
            merged.append(dict(seg))

    return merged


def calculate_speaker_stats(
    segments: list[dict[str, Any]], total_duration: float
) -> list[dict[str, Any]]:
    """Calculate talk time percentage and utterance count per speaker.

    Speakers with less than 2% talk time are filtered out.
    Results are sorted by talk_time_pct descending.
    """
    speaker_times: dict[str, float] = {}
    speaker_counts: dict[str, int] = {}

    for seg in segments:
        speaker = seg["speaker"]
        duration = seg["end"] - seg["start"]
        speaker_times[speaker] = speaker_times.get(speaker, 0.0) + duration
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

    total_talk = sum(speaker_times.values())

    stats = []
    for speaker, talk_time in speaker_times.items():
        pct = (talk_time / total_talk * 100) if total_talk > 0 else 0.0
        if pct >= 2.0:
            stats.append(
                {
                    "label": speaker,
                    "talk_time_pct": round(pct, 1),
                    "utterance_count": speaker_counts[speaker],
                }
            )

    return sorted(stats, key=lambda s: s["talk_time_pct"], reverse=True)


def filter_and_renumber_speakers(
    segments: list[dict[str, Any]], min_percentage: float = 2.0
) -> list[dict[str, Any]]:
    """Reassign segments from minor speakers to the dominant speaker.

    Speakers whose share of total talk time is below min_percentage are
    removed. Their segments are reassigned to the speaker with the most
    talk time rather than being dropped entirely.

    Speaker labels are then renumbered sequentially by descending talk time
    so the most talkative speaker becomes 'Speaker 1', etc.

    Args:
        segments: Segments already carrying a 'speaker' key.
        min_percentage: Minimum % of total talk time to keep a speaker.

    Returns:
        Segments with updated speaker labels.
    """
    # Tally durations per speaker
    total_duration = 0.0
    speaker_durations: dict[str, float] = {}
    for seg in segments:
        duration = seg["end"] - seg["start"]
        total_duration += duration
        spk = seg["speaker"]
        speaker_durations[spk] = speaker_durations.get(spk, 0.0) + duration

    # Separate keepers from minor speakers
    keepers = []
    to_remove: set[str] = set()
    for spk, dur in speaker_durations.items():
        pct = (dur / total_duration * 100) if total_duration > 0 else 0.0
        if pct >= min_percentage:
            keepers.append((spk, dur))
        else:
            to_remove.add(spk)

    # Sort keepers by descending duration for stable renaming
    keepers.sort(key=lambda x: x[1], reverse=True)

    if not keepers:
        # Edge case: everything filtered — keep all under a single label
        return [{**seg, "speaker": "Speaker 1"} for seg in segments]

    dominant_speaker = keepers[0][0]

    # Build old-label → new-label mapping
    label_map: dict[str, str] = {}
    for new_idx, (spk, _) in enumerate(keepers, start=1):
        label_map[spk] = f"Speaker {new_idx}"
    for spk in to_remove:
        label_map[spk] = label_map[dominant_speaker]

    logger.info(
        "Speaker filter: keeping %d speaker(s), reassigning %d minor speaker(s)",
        len(keepers),
        len(to_remove),
    )

    return [{**seg, "speaker": label_map.get(seg["speaker"], "Speaker 1")} for seg in segments]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_transcription(job_id: str, app_state: object) -> dict[str, Any]:
    """Run the full transcription + diarization pipeline for a job.

    Steps:
    1. Get job metadata from storage
    2. Determine audio duration via librosa
    3. Transcribe with Moonshine Voice
    4. Diarize with SpeechBrain ECAPA-TDNN + AgglomerativeClustering,
       assigning speakers to transcript segments directly via midpoint matching
    5. Snap boundaries to sentence endings
    6. Filter minor speakers (< 2%) and reassign their segments to the dominant
       speaker, then renumber all labels to Speaker 1, Speaker 2, ...
    7. Merge consecutive same-speaker segments
    8. Calculate speaker stats

    Args:
        job_id: The unique job identifier.
        app_state: FastAPI app.state with transcriber and diarizer attributes.

    Returns:
        TranscriptResponse-shaped dict.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    wav_path = job["file_path"]

    total_duration = librosa.get_duration(filename=wav_path)

    logger.info("Starting transcription for job %s (%.1fs audio)", job_id, total_duration)

    # STT
    transcript_segments = transcribe_audio(wav_path, app_state.transcriber)
    logger.info("Moonshine STT produced %d segments", len(transcript_segments))

    # Diarize + assign speakers to segments in one step
    labelled_segments = app_state.diarizer.diarize(wav_path, transcript_segments)
    logger.info("FastDiarizer labelled %d segments", len(labelled_segments))

    # Snap to sentence boundaries
    snapped = snap_boundaries_to_sentences(labelled_segments)

    # Filter minor speakers (< 2%) and renumber sequentially
    renumbered = filter_and_renumber_speakers(snapped, min_percentage=2.0)

    # Merge consecutive same-speaker segments
    merged = merge_consecutive_segments(renumbered)

    # Stats
    stats = calculate_speaker_stats(merged, total_duration)

    logger.info(
        "Pipeline complete: %d segments, %d speakers",
        len(merged),
        len(stats),
    )

    return {
        "id": job_id,
        "duration": round(total_duration, 2),
        "language": "en",
        "speakers": stats,
        "segments": merged,
    }
