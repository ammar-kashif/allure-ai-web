"""Moonshine Voice STT + pyannote speaker diarization pipeline.

Provides the full transcription pipeline: audio -> STT segments -> diarization
-> speaker alignment -> label remapping -> segment merging -> speaker stats.
"""

import logging
from typing import Any

import torchaudio

from storage import get_job

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Moonshine STT
# ---------------------------------------------------------------------------

class FileTranscriptListener:
    """Collects TranscriptLine objects from Moonshine Voice Transcriber."""

    def __init__(self):
        self.lines: list = []
        self.current_line = None

    def on_line_started(self, line):
        self.current_line = line

    def on_line_text_changed(self, line):
        self.current_line = line

    def on_line_completed(self, line):
        self.lines.append(line)


def transcribe_audio(wav_path: str, transcriber) -> list[dict[str, Any]]:
    """Transcribe a WAV file using Moonshine Voice.

    Args:
        wav_path: Path to 16kHz mono WAV file.
        transcriber: Moonshine Voice Transcriber instance.

    Returns:
        List of segment dicts with start, end, text, confidence keys.
    """
    from moonshine_voice import load_wav_file

    listener = FileTranscriptListener()
    transcriber.listener = listener

    audio_data, sample_rate = load_wav_file(wav_path)

    transcriber.start()
    chunk_size = int(0.1 * sample_rate)
    for i in range(0, len(audio_data), chunk_size):
        transcriber.add_audio(audio_data[i : i + chunk_size], sample_rate)
    transcriber.stop()

    segments = []
    for line in listener.lines:
        confidence = getattr(line, "confidence", 1.0) or 1.0
        speaker_id = getattr(line, "speaker_id", None)
        if speaker_id is not None:
            logger.debug(
                "Moonshine speaker_id detected: %s (not used -- pyannote is primary)",
                speaker_id,
            )
        segments.append(
            {
                "start": line.start_time,
                "end": line.end_time,
                "text": line.text.strip(),
                "confidence": confidence,
            }
        )

    return segments


# ---------------------------------------------------------------------------
# Pyannote diarization
# ---------------------------------------------------------------------------


def diarize_audio(wav_path: str, pipeline) -> list[dict[str, Any]]:
    """Run pyannote speaker diarization on a WAV file.

    Args:
        wav_path: Path to WAV file.
        pipeline: Loaded pyannote Pipeline instance.

    Returns:
        List of diarization segment dicts with start, end, speaker keys.
    """
    diarization = pipeline(wav_path)
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            {
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker,
            }
        )
    return segments


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


def remap_speaker_labels(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remap pyannote speaker labels to 'Speaker 1', 'Speaker 2', etc.

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

    Speakers with less than 1% talk time are filtered out.
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
        if pct >= 1.0:
            stats.append(
                {
                    "label": speaker,
                    "talk_time_pct": round(pct, 1),
                    "utterance_count": speaker_counts[speaker],
                }
            )

    return sorted(stats, key=lambda s: s["talk_time_pct"], reverse=True)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_transcription(job_id: str, app_state: object) -> dict[str, Any]:
    """Run the full transcription + diarization pipeline for a job.

    Steps:
    1. Get job metadata from storage
    2. Determine audio duration via torchaudio
    3. Transcribe with Moonshine Voice
    4. Diarize with pyannote
    5. Align transcript segments with speaker labels
    6. Remap labels to Speaker 1, Speaker 2, ...
    7. Merge consecutive same-speaker segments
    8. Calculate speaker stats and filter <1% speakers
    9. Filter segments from removed speakers

    Args:
        job_id: The unique job identifier.
        app_state: FastAPI app.state with transcriber and diarization attributes.

    Returns:
        TranscriptResponse-shaped dict.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    wav_path = job["file_path"]

    # Get audio duration
    info = torchaudio.info(wav_path)
    total_duration = info.num_frames / info.sample_rate

    logger.info("Starting transcription for job %s (%.1fs audio)", job_id, total_duration)

    # STT
    transcript_segments = transcribe_audio(wav_path, app_state.transcriber)
    logger.info("Moonshine STT produced %d segments", len(transcript_segments))

    # Diarization
    diarization_segments = diarize_audio(wav_path, app_state.diarization)
    logger.info("Pyannote produced %d diarization segments", len(diarization_segments))

    # Align
    aligned = align_transcript_with_speakers(transcript_segments, diarization_segments)

    # Remap labels
    remapped = remap_speaker_labels(aligned)

    # Merge consecutive
    merged = merge_consecutive_segments(remapped)

    # Stats (before filtering so we can identify <1% speakers)
    stats = calculate_speaker_stats(merged, total_duration)

    # Filter segments from speakers below 1% threshold
    valid_speakers = {s["label"] for s in stats}
    filtered_segments = [s for s in merged if s["speaker"] in valid_speakers]

    logger.info(
        "Pipeline complete: %d segments, %d speakers",
        len(filtered_segments),
        len(stats),
    )

    return {
        "id": job_id,
        "duration": round(total_duration, 2),
        "language": "en",
        "speakers": stats,
        "segments": filtered_segments,
    }
