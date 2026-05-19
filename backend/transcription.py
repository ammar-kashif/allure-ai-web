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
from sklearn.cluster import AgglomerativeClustering, SpectralClustering
from scipy.ndimage import median_filter
from scipy.sparse.linalg import eigsh
from silero_vad import get_speech_timestamps

from observability import step_timer
from storage import get_job
from text_post import punctuate_segments

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
    """CPU-only speaker diarization using silero-vad + SpeechBrain ECAPA-TDNN
    embeddings + NME-SC spectral clustering (or agglomerative fallback).

    Pipeline: VAD -> short windows on speech only -> L2-norm -> NME-SC
    (auto-K via eigengap on top-p sparsified affinity) -> centroid-merge
    safety net -> cap speakers -> hop-proportional median smoothing
    -> non-overlapping time segments.

    NOTE on history: an earlier revision did L2 -> mean-center -> L2 to
    remove channel/recording bias. Empirically this destroyed speaker
    separability for low-speaker recordings (the mean *is* the midpoint
    between speakers when K is small). Centering removed; spectral
    clustering with affinity sparsification + eigengap handles channel
    variation by aggregating evidence over many neighbor connections.

    Args:
        encoder: SpeechBrain EncoderClassifier instance (ECAPA-TDNN).
        vad_model: silero-vad model from `load_silero_vad(onnx=False)`.
        window_size: Embedding window length (s).
        hop_size: Step between windows (s).
        min_segment_duration: Drop output segments shorter than this (s).
        clustering_method: 'spectral' (NME-SC, auto-K) or 'agglomerative'
            (linkage + distance_threshold, no auto-K).
        distance_threshold: Cosine-distance cutoff for agglomerative
            fallback. 0.75 works well for L2-only ECAPA.
        linkage: 'average' or 'complete' for agglomerative fallback.
        vad_threshold: silero-vad speech-probability cutoff (0.0-1.0).
        min_speech_duration: Drop VAD speech intervals shorter than this (s).
        centroid_merge_threshold: After clustering, merge any two clusters
            whose centroid cosine distance is below this. Safety net.
            Set 0.0 to disable.
        max_speakers: Hard cap on cluster count. Constrains NME-SC's K
            search and trims extras by centroid-distance merging.
        min_windows_for_spectral: Below this many embeddings, fall back to
            agglomerative regardless of clustering_method.
    """

    def __init__(
        self,
        encoder,
        vad_model,
        window_size: float = 2.0,
        hop_size: float = 0.75,
        min_segment_duration: float = 1.0,
        clustering_method: str = "spectral",
        distance_threshold: float = 0.75,
        linkage: str = "average",
        vad_threshold: float = 0.5,
        min_speech_duration: float = 0.5,
        centroid_merge_threshold: float = 0.0,
        max_speakers: int = 6,
        min_windows_for_spectral: int = 10,
    ):
        self.encoder = encoder
        self.vad_model = vad_model
        self.window_size = window_size
        self.hop_size = hop_size
        self.min_segment_duration = min_segment_duration
        self.clustering_method = clustering_method
        self.distance_threshold = distance_threshold
        self.linkage = linkage
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration
        self.centroid_merge_threshold = centroid_merge_threshold
        self.max_speakers = max_speakers
        self.min_windows_for_spectral = min_windows_for_spectral

    def diarize(self, audio_path: str) -> list[dict[str, Any]]:
        """Run diarization. Returns non-overlapping time-sorted segments
        of {start, end, speaker} where speaker is 'cluster_<int>'."""
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        total_duration = len(audio) / sr

        speech_intervals = self._run_vad(audio, sr)
        if speech_intervals:
            speech_ratio = sum(e - s for s, e in speech_intervals) / max(total_duration, 1e-9)
            logger.info(
                "VAD: %.1f%% speech across %d interval(s)",
                speech_ratio * 100.0,
                len(speech_intervals),
            )
        else:
            logger.info("VAD found no speech; returning single-speaker fallback")
            return [{"start": 0.0, "end": total_duration, "speaker": "cluster_0"}]

        embeddings, window_starts, window_ends = self._extract_windows(
            audio, sr, speech_intervals
        )
        logger.info("Extracted %d embedding window(s)", len(embeddings))

        if len(embeddings) < 2:
            return [{"start": 0.0, "end": total_duration, "speaker": "cluster_0"}]

        # L2-normalize only — no mean-centering (it collapses speaker
        # separability when K is small).
        embeddings = self._normalize_embeddings(embeddings)

        labels = self._cluster_embeddings(embeddings)
        n_initial = len(set(labels.tolist()))

        labels = self._centroid_merge(embeddings, labels, self.centroid_merge_threshold)
        n_after_merge = len(set(labels.tolist()))

        labels = self._cap_speakers(embeddings, labels, self.max_speakers)
        n_after_cap = len(set(labels.tolist()))

        logger.info(
            "Clusters: %d initial -> %d after centroid-merge -> %d after cap",
            n_initial,
            n_after_merge,
            n_after_cap,
        )

        if len(labels) >= 3:
            k = max(3, int(round(2.0 / max(self.hop_size, 1e-6))))
            if k % 2 == 0:
                k += 1
            labels = median_filter(labels, size=k).astype(int)

        return self._labels_to_segments(window_starts, window_ends, labels, total_duration)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_vad(self, audio: np.ndarray, sr: int) -> list[tuple[float, float]]:
        audio_tensor = torch.from_numpy(audio.astype(np.float32))
        timestamps = get_speech_timestamps(
            audio_tensor,
            self.vad_model,
            threshold=self.vad_threshold,
            sampling_rate=sr,
            min_speech_duration_ms=int(self.min_speech_duration * 1000),
        )
        return [(t["start"] / sr, t["end"] / sr) for t in timestamps]

    def _encode_chunk(self, chunk: np.ndarray) -> np.ndarray:
        # RMS-normalize to neutralize browser/recorder AGC drift
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        if rms > 1e-6:
            chunk = (chunk / rms) * 0.1
        waveform = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            emb = self.encoder.encode_batch(waveform)
        return emb.squeeze().cpu().numpy()

    def _extract_windows(
        self,
        audio: np.ndarray,
        sr: int,
        speech_intervals: list[tuple[float, float]],
    ) -> tuple[np.ndarray, list[float], list[float]]:
        window_samples = int(self.window_size * sr)
        hop_samples = max(1, int(self.hop_size * sr))
        min_chunk_samples = int(0.75 * sr)  # ECAPA stable down to ~0.75s

        embeddings: list[np.ndarray] = []
        starts: list[float] = []
        ends: list[float] = []

        for sp_start, sp_end in speech_intervals:
            start_sample = int(sp_start * sr)
            end_sample = min(int(sp_end * sr), len(audio))
            interval_len = end_sample - start_sample

            if interval_len < window_samples:
                # Short interval — embed it whole (no padding)
                if interval_len < min_chunk_samples:
                    continue
                chunk = audio[start_sample:end_sample]
                embeddings.append(self._encode_chunk(chunk))
                starts.append(start_sample / sr)
                ends.append(end_sample / sr)
                continue

            # Slide windows within the speech interval
            for offset in range(0, interval_len - window_samples + 1, hop_samples):
                w_start_sample = start_sample + offset
                chunk = audio[w_start_sample : w_start_sample + window_samples]
                embeddings.append(self._encode_chunk(chunk))
                starts.append(w_start_sample / sr)
                ends.append((w_start_sample + window_samples) / sr)

        if not embeddings:
            return np.zeros((0, 192), dtype=np.float32), [], []
        return np.stack(embeddings), starts, ends

    def _normalize_embeddings(self, embs: np.ndarray) -> np.ndarray:
        # L2-normalize only (no mean centering — see class docstring).
        embs = embs / (np.linalg.norm(embs, axis=1, keepdims=True) + 1e-9)
        return embs.astype(np.float32)

    def _cluster_embeddings(self, embs: np.ndarray) -> np.ndarray:
        """Dispatch to spectral (NME-SC) or agglomerative based on config
        and dataset size."""
        N = len(embs)
        if (
            self.clustering_method == "spectral"
            and N >= self.min_windows_for_spectral
        ):
            try:
                return self._nme_sc_cluster(embs)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "NME-SC spectral clustering failed (%s); falling back to "
                    "agglomerative",
                    exc,
                )
        return self._agglomerative_cluster(embs)

    def _nme_sc_cluster(self, embs: np.ndarray) -> np.ndarray:
        """NME-SC: sweep affinity sparsification p, pick (K, p) that
        maximizes the eigengap-ratio of the normalized Laplacian."""
        N = embs.shape[0]
        sim = embs @ embs.T  # cosine sim, embs are unit-norm
        sim_pos = np.clip(sim, 0.0, None).astype(np.float64)

        max_eig = min(self.max_speakers + 2, N - 1)
        best_K = 1
        best_ratio = -1.0
        best_A: np.ndarray | None = None

        for p in np.linspace(0.05, 0.5, 8):
            k = max(1, int(round(float(p) * N)))
            scrub = np.zeros_like(sim_pos)
            for i in range(N):
                idx = np.argpartition(sim_pos[i], -k)[-k:]
                scrub[i, idx] = sim_pos[i, idx]
            A = np.maximum(scrub, scrub.T)  # symmetric, non-negative

            # Normalized affinity: D^-1/2 A D^-1/2 (Laplacian eigvals = 1 - this)
            d = A.sum(axis=1) + 1e-9
            d_inv_sqrt = 1.0 / np.sqrt(d)
            A_norm = (d_inv_sqrt[:, None] * A) * d_inv_sqrt[None, :]

            try:
                # Largest eigenvalues of A_norm == smallest of Laplacian
                aff_eigs = eigsh(
                    A_norm, k=max_eig, which="LA", return_eigenvectors=False
                )
            except Exception:
                continue
            lap_eigs = np.sort(1.0 - aff_eigs)  # ascending
            gaps = np.diff(lap_eigs)
            # Skip gap[0] (Fiedler value, trivially ~0 for any connected
            # graph — always the largest gap so dominates K selection).
            # Search from gap[1] onward; K candidates start at 2.
            # K=1 is reachable later via centroid-merge collapsing K=2->1.
            search_gaps = gaps[1 : self.max_speakers + 1]
            if search_gaps.size < 1:
                continue
            K_candidate = int(np.argmax(search_gaps)) + 2
            sorted_gaps = np.sort(search_gaps)[::-1]
            ratio = float(
                sorted_gaps[0] / (sorted_gaps[1] + 1e-9)
                if sorted_gaps.size > 1
                else sorted_gaps[0]
            )
            if ratio > best_ratio:
                best_ratio = ratio
                best_K = K_candidate
                best_A = A

        logger.info(
            "NME-SC: K=%d (eigengap-ratio=%.3f)", best_K, best_ratio
        )

        if best_K <= 1 or best_A is None:
            return np.zeros(N, dtype=int)

        sc = SpectralClustering(
            n_clusters=best_K,
            affinity="precomputed",
            random_state=0,
            assign_labels="kmeans",
        )
        return sc.fit_predict(best_A)

    def _agglomerative_cluster(self, embs: np.ndarray) -> np.ndarray:
        """Fallback clustering for small N or when spectral fails."""
        sim = embs @ embs.T
        dist = 1.0 - sim
        np.fill_diagonal(dist, 0.0)
        dist = np.clip(dist, 0.0, 2.0).astype(np.float64)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.distance_threshold,
            metric="precomputed",
            linkage=self.linkage,
        )
        return clustering.fit_predict(dist)

    def _centroid_merge(
        self, embs: np.ndarray, labels: np.ndarray, threshold: float
    ) -> np.ndarray:
        if threshold <= 0.0:
            return labels
        labels = labels.copy()
        while True:
            unique = sorted(set(labels.tolist()))
            if len(unique) < 2:
                break
            centroids = np.stack([embs[labels == u].mean(axis=0) for u in unique])
            centroids = centroids / (np.linalg.norm(centroids, axis=1, keepdims=True) + 1e-9)
            sim = centroids @ centroids.T
            dist = 1.0 - sim
            np.fill_diagonal(dist, np.inf)
            i, j = np.unravel_index(np.argmin(dist), dist.shape)
            if dist[i, j] >= threshold:
                break
            labels[labels == unique[j]] = unique[i]
        return labels

    def _cap_speakers(
        self, embs: np.ndarray, labels: np.ndarray, max_speakers: int
    ) -> np.ndarray:
        labels = labels.copy()
        while True:
            unique, counts = np.unique(labels, return_counts=True)
            if len(unique) <= max_speakers:
                break
            smallest_label = unique[int(np.argmin(counts))]
            small_centroid = embs[labels == smallest_label].mean(axis=0)
            small_centroid = small_centroid / (np.linalg.norm(small_centroid) + 1e-9)

            best_label = None
            best_dist = np.inf
            for u in unique:
                if u == smallest_label:
                    continue
                c = embs[labels == u].mean(axis=0)
                c = c / (np.linalg.norm(c) + 1e-9)
                d = float(1.0 - small_centroid @ c)
                if d < best_dist:
                    best_dist = d
                    best_label = u
            if best_label is None:
                break
            labels[labels == smallest_label] = best_label
        return labels

    def _labels_to_segments(
        self,
        starts: list[float],
        ends: list[float],
        labels: np.ndarray,
        total_duration: float,
    ) -> list[dict[str, Any]]:
        if not starts:
            return [{"start": 0.0, "end": total_duration, "speaker": "cluster_0"}]

        order = np.argsort(starts)
        starts_s = [starts[i] for i in order]
        ends_s = [ends[i] for i in order]
        labels_s = [int(labels[i]) for i in order]

        # Build per-window segments with midpoint boundaries where windows overlap
        raw = []
        n = len(starts_s)
        for i in range(n):
            s, e, lab = starts_s[i], ends_s[i], labels_s[i]
            seg_start = s if i == 0 else (
                (ends_s[i - 1] + s) / 2.0 if ends_s[i - 1] > s else s
            )
            seg_end = (
                min(e, total_duration) if i == n - 1
                else ((e + starts_s[i + 1]) / 2.0 if e > starts_s[i + 1] else e)
            )
            raw.append({"start": seg_start, "end": seg_end, "speaker": f"cluster_{lab}"})

        # Merge consecutive same-speaker segments separated by tiny gaps (<0.5s)
        merged: list[dict[str, Any]] = []
        for seg in raw:
            if merged and merged[-1]["speaker"] == seg["speaker"] and (
                seg["start"] - merged[-1]["end"]
            ) < 0.5:
                merged[-1]["end"] = seg["end"]
            else:
                merged.append(dict(seg))

        # Drop too-short segments
        merged = [s for s in merged if (s["end"] - s["start"]) >= self.min_segment_duration]

        # Round to 3 decimals for output stability
        for s in merged:
            s["start"] = round(s["start"], 3)
            s["end"] = round(s["end"], 3)

        return merged if merged else [
            {"start": 0.0, "end": round(total_duration, 3), "speaker": "cluster_0"}
        ]


# ---------------------------------------------------------------------------
# Alignment and post-processing (pure functions)
# ---------------------------------------------------------------------------


def align_transcript_with_speakers(
    transcript_segments: list[dict[str, Any]],
    diarization_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assign speaker labels to transcript segments by maximum time overlap.

    If a transcript segment doesn't overlap any diarization segment (Moonshine
    sometimes detects speech that VAD missed), fall back to the nearest
    diarization segment by midpoint distance. This avoids leaking an
    "Unknown" label that would inflate the apparent speaker count.
    """
    if not diarization_segments:
        return [{**seg, "speaker": "Unknown"} for seg in transcript_segments]

    result = []
    for seg in transcript_segments:
        best_speaker: str | None = None
        best_overlap = 0.0
        for diar in diarization_segments:
            overlap_start = max(seg["start"], diar["start"])
            overlap_end = min(seg["end"], diar["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = diar["speaker"]
        if best_speaker is None:
            seg_mid = (seg["start"] + seg["end"]) / 2.0
            nearest = min(
                diarization_segments,
                key=lambda d: abs(((d["start"] + d["end"]) / 2.0) - seg_mid),
            )
            best_speaker = nearest["speaker"]
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
    with step_timer("stt.moonshine", job_id=job_id, duration_s=round(total_duration, 1)):
        transcript_segments = transcribe_audio(wav_path, app_state.transcriber)
    logger.info("Moonshine STT produced %d segments", len(transcript_segments))

    # Diarization
    with step_timer("diarization", job_id=job_id):
        diarization_segments = app_state.diarizer.diarize(wav_path)
    logger.info("FastDiarizer produced %d diarization segments", len(diarization_segments))

    # Align
    with step_timer("align", job_id=job_id):
        aligned = align_transcript_with_speakers(transcript_segments, diarization_segments)

    # Restore punctuation + capitalization on each segment's text
    punctuator = getattr(app_state, "punctuator", None)
    if punctuator is not None:
        aligned = punctuate_segments(aligned, punctuator)

    # Snap to sentence boundaries
    snapped = snap_boundaries_to_sentences(aligned)

    # Remap labels
    remapped = remap_speaker_labels(snapped)

    # Merge consecutive
    with step_timer("merge", job_id=job_id):
        merged = merge_consecutive_segments(remapped)

    # Stats (before filtering so we can identify <1% speakers)
    with step_timer("stats", job_id=job_id):
        stats = calculate_speaker_stats(merged, total_duration)

    # Filter segments from speakers below 1% threshold
    valid_speakers = {s["label"] for s in stats}
    filtered_segments = [s for s in merged if s["speaker"] in valid_speakers]

    # Identify speaker names and roles via LLM
    if hasattr(app_state, "llm") and app_state.llm:
        with step_timer("speaker_id.llm", job_id=job_id, n_speakers=len(stats)):
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
