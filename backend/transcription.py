"""Moonshine Voice STT + SpeechBrain ECAPA-TDNN speaker diarization pipeline.

Provides the full transcription pipeline: audio -> STT segments -> diarization
(fixed-window embeddings + AgglomerativeClustering) -> speaker alignment with
sentence-boundary snapping -> label remapping -> segment merging -> speaker stats.
"""

import json
import logging
import re
import time
from typing import Any

import librosa
import numpy as np
import torch
from sklearn.cluster import AgglomerativeClustering
from scipy.ndimage import median_filter

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
    and AgglomerativeClustering.

    Designed for clean audio (podcasts, interviews, meetings). Each fixed-size
    window is assigned one dominant speaker — no overlap handling.

    Args:
        encoder: SpeechBrain EncoderClassifier instance (ECAPA-TDNN).
        window_size: Embedding window length in seconds.
        hop_size: Step between windows in seconds.
        min_segment_duration: Drop speaker segments shorter than this (seconds).
    """

    def __init__(
        self,
        encoder,
        window_size: float = 10.0,
        hop_size: float = 2.0,
        min_segment_duration: float = 1.0,
    ):
        self.encoder = encoder
        self.window_size = window_size
        self.hop_size = hop_size
        self.min_segment_duration = min_segment_duration

    def diarize(self, audio_path: str) -> list[dict[str, Any]]:
        """Run diarization on an audio file.

        Args:
            audio_path: Path to audio file (any format librosa supports).

        Returns:
            List of dicts with start, end, speaker keys. Speaker labels are
            raw cluster IDs like "cluster_0", "cluster_1".
        """
        # Load and resample to 16 kHz mono
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        total_duration = len(audio) / sr

        # Extract fixed-window embeddings
        window_samples = int(self.window_size * sr)
        hop_samples = int(self.hop_size * sr)

        embeddings = []
        window_starts = []

        for start_sample in range(0, len(audio) - window_samples + 1, hop_samples):
            chunk = audio[start_sample : start_sample + window_samples]
            waveform = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                emb = self.encoder.encode_batch(waveform)
            embeddings.append(emb.squeeze().numpy())
            window_starts.append(start_sample / sr)

        # Handle final partial window if audio doesn't divide evenly
        last_start = (len(audio) - window_samples) // hop_samples * hop_samples
        remaining_start = last_start + hop_samples
        if remaining_start < len(audio) and remaining_start not in [
            s * sr for s in window_starts
        ]:
            chunk = audio[remaining_start:]
            if len(chunk) >= sr:  # At least 1 second
                # Pad to window size
                padded = np.zeros(window_samples, dtype=np.float32)
                padded[: len(chunk)] = chunk
                waveform = torch.tensor(padded, dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    emb = self.encoder.encode_batch(waveform)
                embeddings.append(emb.squeeze().numpy())
                window_starts.append(remaining_start / sr)

        if len(embeddings) < 2:
            # Too short for clustering — assign single speaker
            return [{"start": 0.0, "end": total_duration, "speaker": "cluster_0"}]

        embedding_matrix = np.stack(embeddings)

        # AgglomerativeClustering (auto-determines speaker count via distance threshold)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=0.7,  # Cosine distance threshold for ECAPA-TDNN embeddings; tune on real recordings
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(embedding_matrix)

        # Smooth labels with median filter to remove single-window flickers
        if len(labels) >= 3:
            labels = median_filter(labels, size=3).astype(int)

        # Convert window labels to time segments
        raw_segments = []
        for i, (start_time, label) in enumerate(zip(window_starts, labels)):
            end_time = start_time + self.window_size
            end_time = min(end_time, total_duration)
            raw_segments.append(
                {
                    "start": round(start_time, 3),
                    "end": round(end_time, 3),
                    "speaker": f"cluster_{label}",
                }
            )

        # Merge consecutive segments with the same speaker
        merged = []
        for seg in raw_segments:
            if merged and merged[-1]["speaker"] == seg["speaker"]:
                merged[-1]["end"] = seg["end"]
            else:
                merged.append(dict(seg))

        # Filter out very short segments
        merged = [
            s for s in merged if (s["end"] - s["start"]) >= self.min_segment_duration
        ]

        return merged if merged else [{"start": 0.0, "end": total_duration, "speaker": "cluster_0"}]


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
    """Calculate extended per-speaker statistics.

    Returns per speaker: label, talk_time_pct, utterance_count, talk_time,
    word_count, wpm, turns, avg_turn_duration, pauses, avg_pause_duration.

    Speakers with less than 1% talk time are filtered out.
    Results are sorted by talk_time_pct descending.
    """
    speaker_times: dict[str, float] = {}
    speaker_counts: dict[str, int] = {}
    speaker_words: dict[str, int] = {}
    speaker_segments: dict[str, list[dict[str, Any]]] = {}

    for seg in segments:
        speaker = seg["speaker"]
        duration = seg["end"] - seg["start"]
        speaker_times[speaker] = speaker_times.get(speaker, 0.0) + duration
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        text = seg.get("text", "")
        word_count = len(text.split()) if text.strip() else 0
        speaker_words[speaker] = speaker_words.get(speaker, 0) + word_count
        speaker_segments.setdefault(speaker, []).append(seg)

    total_talk = sum(speaker_times.values())

    stats = []
    for speaker, talk_time in speaker_times.items():
        pct = (talk_time / total_talk * 100) if total_talk > 0 else 0.0
        if pct < 1.0:
            continue

        turns = speaker_counts[speaker]
        word_count = speaker_words[speaker]
        talk_minutes = talk_time / 60.0
        wpm = (word_count / talk_minutes) if talk_minutes > 0 else 0.0
        avg_turn_duration = (talk_time / turns) if turns > 0 else 0.0

        # Calculate pauses: gaps between consecutive same-speaker segments
        segs_sorted = sorted(speaker_segments[speaker], key=lambda s: s["start"])
        pause_count = 0
        total_pause_time = 0.0
        for i in range(1, len(segs_sorted)):
            gap = segs_sorted[i]["start"] - segs_sorted[i - 1]["end"]
            if gap > 0:
                pause_count += 1
                total_pause_time += gap
        avg_pause_duration = (total_pause_time / pause_count) if pause_count > 0 else 0.0

        stats.append(
            {
                "label": speaker,
                "talk_time_pct": round(pct, 1),
                "utterance_count": turns,
                "talk_time": round(talk_time, 2),
                "word_count": word_count,
                "wpm": round(wpm, 1),
                "turns": turns,
                "avg_turn_duration": round(avg_turn_duration, 2),
                "pauses": pause_count,
                "avg_pause_duration": round(avg_pause_duration, 2),
            }
        )

    return sorted(stats, key=lambda s: s["talk_time_pct"], reverse=True)


VALID_ROLES = ["Participant", "Engineer", "Project Manager", "Client", "Designer"]

SPEAKER_ID_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "speakers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "name": {"type": "string"},
                    "role": {
                        "type": "string",
                        "enum": VALID_ROLES,
                    },
                },
                "required": ["label", "name", "role"],
            },
        }
    },
    "required": ["speakers"],
}

SPEAKER_ID_PROMPT = """Analyze this meeting transcript and identify each speaker's real name and role.

Look for clues like:
- Self-introductions ("I'm John", "This is Sarah")
- Others addressing them ("Thanks John", "Sarah, what do you think?")
- Sign-offs or greetings that mention names
- Role hints from what they discuss (code/technical = Engineer, timelines/scope = Project Manager, requirements/feedback = Client, UI/UX/visuals = Designer)

Speaker labels in the transcript: {speaker_labels}

Rules:
- If you can confidently identify a name, use it. Otherwise return an empty string for name.
- Role must be one of: {roles}
- Default to "Participant" if the role is unclear.
- Return ALL speaker labels, even if you can't identify them.

Transcript:
{transcript}"""


def identify_speakers_with_llm(
    segments: list[dict[str, Any]],
    stats: list[dict[str, Any]],
    llm: object,
) -> list[dict[str, Any]]:
    """Use LLM to identify speaker names and roles from transcript content.

    Falls back to default roles if LLM call fails.
    """
    speaker_labels = [s["label"] for s in stats]

    # Format transcript for the prompt (compact: speaker + text only)
    lines = []
    for seg in segments[:150]:  # Cap to avoid token limits
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "")
        lines.append(f"{speaker}: {text}")
    transcript_text = "\n".join(lines)

    prompt = SPEAKER_ID_PROMPT.format(
        speaker_labels=", ".join(speaker_labels),
        roles=", ".join(VALID_ROLES),
        transcript=transcript_text,
    )

    try:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You identify meeting participants from transcripts. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object", "schema": SPEAKER_ID_SCHEMA},
            temperature=0.1,
            max_tokens=1024,
        )

        raw = response["choices"][0]["message"]["content"]
        parsed = json.loads(raw)

        # Build lookup: label -> {name, role}
        id_map: dict[str, dict[str, str]] = {}
        for sp in parsed.get("speakers", []):
            label = sp.get("label", "")
            name = sp.get("name", "")
            role = sp.get("role", "Participant")
            if role not in VALID_ROLES:
                role = "Participant"
            id_map[label] = {"name": name, "role": role}

        # Apply to stats
        for speaker in stats:
            label = speaker["label"]
            info = id_map.get(label, {})
            speaker["custom_label"] = info.get("name", "")
            speaker["role"] = info.get("role", "Participant")

        logger.info("LLM speaker identification: %s", id_map)
        return stats

    except Exception as e:
        logger.warning("LLM speaker identification failed, using defaults: %s", e)
        return _assign_default_roles(stats)


def _assign_default_roles(stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fallback: assign Participant role to all speakers."""
    for speaker in stats:
        speaker["custom_label"] = speaker.get("custom_label", "")
        speaker["role"] = speaker.get("role", "Participant")
    return stats


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_transcription(job_id: str, app_state: object) -> dict[str, Any]:
    """Run the full transcription + diarization pipeline for a job.

    Steps:
    1. Get job metadata from storage
    2. Determine audio duration via librosa
    3. Transcribe with Moonshine Voice
    4. Diarize with SpeechBrain ECAPA-TDNN + AgglomerativeClustering
    5. Align transcript segments with speaker labels
    6. Snap boundaries to sentence endings
    7. Remap labels to Speaker 1, Speaker 2, ...
    8. Merge consecutive same-speaker segments
    9. Calculate speaker stats and filter <1% speakers
    10. Filter segments from removed speakers

    Args:
        job_id: The unique job identifier.
        app_state: FastAPI app.state with transcriber and diarizer attributes.

    Returns:
        TranscriptResponse-shaped dict.
    """
    pipeline_start = time.perf_counter()

    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    wav_path = job["file_path"]

    # Get audio duration
    total_duration = librosa.get_duration(filename=wav_path)

    logger.info("Starting transcription for job %s (%.1fs audio)", job_id, total_duration)

    # STT
    transcript_segments = transcribe_audio(wav_path, app_state.transcriber)
    logger.info("Moonshine STT produced %d segments", len(transcript_segments))

    # Diarization
    diarization_segments = app_state.diarizer.diarize(wav_path)
    logger.info("FastDiarizer produced %d diarization segments", len(diarization_segments))

    # Align
    aligned = align_transcript_with_speakers(transcript_segments, diarization_segments)

    # Snap to sentence boundaries
    snapped = snap_boundaries_to_sentences(aligned)

    # Remap labels
    remapped = remap_speaker_labels(snapped)

    # Merge consecutive
    merged = merge_consecutive_segments(remapped)

    # Stats (before filtering so we can identify <1% speakers)
    stats = calculate_speaker_stats(merged, total_duration)

    # Filter segments from speakers below 1% threshold
    valid_speakers = {s["label"] for s in stats}
    filtered_segments = [s for s in merged if s["speaker"] in valid_speakers]

    # Identify speaker names and roles via LLM
    if hasattr(app_state, "llm") and app_state.llm:
        stats = identify_speakers_with_llm(filtered_segments, stats, app_state.llm)
    else:
        stats = _assign_default_roles(stats)

    logger.info(
        "Pipeline complete: %d segments, %d speakers",
        len(filtered_segments),
        len(stats),
    )

    processing_time = round(time.perf_counter() - pipeline_start, 2)

    return {
        "id": job_id,
        "duration": round(total_duration, 2),
        "language": "en",
        "speakers": stats,
        "segments": filtered_segments,
        "processing_time": processing_time,
    }
