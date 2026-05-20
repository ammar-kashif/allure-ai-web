# Diarization Pipeline — Decisions Log

A running journal of every change we made to `backend/transcription.py:FastDiarizer` and why. Mostly here so we remember what we tried, what worked, and what burned us — and so the next person doesn't repeat the dead ends.

The pipeline lives in `backend/transcription.py`. Defaults are wired in `backend/main.py`'s lifespan and tunable via `DIARIZER_*` environment variables.

---

## 1. Added silero-vad before embedding

**What:** a small speech-detection model runs first and gives us a list of "this part is actually speech" intervals. ECAPA only embeds those.

**Why:** without it, we were embedding silence, breaths, mouse clicks, and music intros as if they were voices — and clustering them as fake speakers. VAD is the single most load-bearing fix in the whole pipeline.

---

## 2. Shrunk the window from 10s → 2s, hop 2s → 0.75s

**What:** ECAPA now sees 2-second chunks of speech instead of 10-second ones, slid every 0.75s.

**Why:** a 10s window in a real conversation averages across speaker turns (people swap every 3–5s), so the embedding becomes a blend of two voices and clusters poorly. Short windows resolve the turn-taking — but only because VAD is now removing the silence that used to pollute short windows.

---

## 3. L2-normalize embeddings

**What:** every ECAPA embedding gets divided by its own magnitude before any distance math.

**Why:** ECAPA doesn't unit-normalize by default, and the raw vector magnitudes correlate with gain and SNR. Cosine distance is only meaningful on unit-length vectors.

---

## 4. Tried mean-centering. Removed it.

**What:** briefly added "subtract the recording's mean embedding from each window" as a channel-adaptation trick borrowed from speaker-recognition lit.

**Why we removed it:** that trick assumes lots of speakers. When there are only two, the recording mean sits *between* the two voices, and subtracting it pushes them into opposite corners — destroying the very speaker separation we're trying to cluster on. Distance histograms went from healthy (47% of pairs < 0.6) to broken (only 1.4% < 0.5). Took a while to spot.

---

## 5. Switched to NME-SC spectral clustering

**What:** instead of AgglomerativeClustering with a hand-tuned distance threshold, we now build a sparsified affinity matrix and pick K from the eigengap of its normalized Laplacian.

**Why:** the agglomerative threshold worked great on one recording and broke on the next. Spectral clustering with eigengap auto-picks K from the data, so we don't need per-recording tuning. It's also what production diarization stacks (NeMo, pyannote) use.

---

## 6. Skip the trivial Fiedler gap (gap[0])

**What:** when selecting K via eigengap, we ignore the first gap and search from `gaps[1:]`.

**Why:** the smallest eigenvalue of any connected graph's normalized Laplacian is always ~0, so `gap[0]` is always the largest. Including it in `argmax` means we'd always pick K=1. This single bug was responsible for our "everything is one speaker" failure mode after the spectral switch — every recording was collapsing.

---

## 7. Top-p affinity scrubbing

**What:** in the affinity matrix we sweep, each row keeps only the top 10% strongest similarities and zeros out the rest. We try a few sparsification levels and pick the one with the cleanest eigengap.

**Why:** noisy weak similarities between unrelated windows confuse spectral clustering and inflate K. Sparsifying makes the algorithm focus on the strongest, most trustworthy connections.

---

## 8. RMS-normalize each chunk before encoding

**What:** scale each 2-second chunk to a constant RMS energy level before ECAPA processes it.

**Why:** browser audio (Chrome's WebRTC) has automatic gain control that drifts across a recording. The same speaker can produce embeddings with different norms across the same call. RMS-normalizing the input evens that out so the model sees a consistent signal.

---

## 9. Hop-proportional median filter on the label sequence

**What:** smooth the per-window cluster labels with a median filter sized to ~2 seconds of windows.

**Why:** kills single-window flickers — a 1.5s blip onto the other speaker doesn't deserve to be its own segment. The kernel size scales with hop so the temporal smoothing window stays roughly constant regardless of how we tune the windowing.

---

## 10. Non-overlapping segments with midpoint boundaries

**What:** when collapsing per-window labels into final segments, adjacent windows of the same speaker merge, and when consecutive windows overlap in time, the boundary lands at the midpoint of their overlap.

**Why:** the old code emitted overlapping diar segments (10s windows at 2s hop overlap by 8s each), which made the downstream "assign speaker by max-overlap" step order-biased and ambiguous. Clean non-overlapping timeline → clean alignment.

---

## 11. Centroid-merge post-pass (and the threshold that burned us)

**What:** after spectral clustering, compute the centroid of each cluster and optionally merge any pair whose centroids are closer than a threshold.

**Why we added it:** spectral clustering occasionally splits one speaker into two clusters (long monologues with tonal/topic changes). Centroid merge cleans those up.

**Why we eventually disabled it (threshold 0.80 → 0.0):** the 0.80 threshold was calibrated to a single mono-speaker recording where the false split had centroid distance ~0.80. Across actual recordings, *real* 2-speaker centroids land at 0.6–0.75 — well below 0.80 — so the merge was systematically eating legitimate K=2 detections. Mono over-detection is rare and easy to fix in the UI; under-detection (1 speaker shown when there are clearly 2+) is what users actually complain about.

---

## 12. Fixed the "Unknown" leak in transcript alignment

**What:** in `align_transcript_with_speakers`, if a transcript segment doesn't temporally overlap any diarization segment, we now fall back to the nearest diar segment by midpoint distance instead of labeling it `"Unknown"`.

**Why:** Moonshine sometimes detects speech that silero-vad missed. Those transcript segments had no overlap with any diar segment, got tagged `"Unknown"`, and after the later `remap_speaker_labels` pass that `"Unknown"` became a phantom `"Speaker N"`. That's literally why one specific 2-speaker meeting was showing as 9 speakers — eight real cluster_X labels plus one phantom Unknown-bucket.

---

## Current defaults (env-tunable)

| Variable | Default | Notes |
|---|---:|---|
| `DIARIZER_WINDOW_SECONDS` | `2.0` | down from 10.0 |
| `DIARIZER_HOP_SECONDS` | `0.75` | |
| `DIARIZER_CLUSTERING_METHOD` | `spectral` | NME-SC; falls back to `agglomerative` if N < `DIARIZER_MIN_WINDOWS_FOR_SPECTRAL` or eigsh fails |
| `DIARIZER_DISTANCE_THRESHOLD` | `0.75` | only used by the agglomerative fallback |
| `DIARIZER_LINKAGE` | `average` | only used by the agglomerative fallback |
| `DIARIZER_VAD_THRESHOLD` | `0.5` | silero-vad probability cutoff |
| `DIARIZER_MIN_SPEECH_SECONDS` | `0.5` | drop tiny VAD blips |
| `DIARIZER_CENTROID_MERGE_THRESHOLD` | `0.0` | disabled — see decision 11 |
| `DIARIZER_MAX_SPEAKERS` | `6` | hard cap; NME-SC won't choose K above this |
| `DIARIZER_MIN_WINDOWS_FOR_SPECTRAL` | `10` | below this, fall back to agglomerative |

---

## When it's wrong

**Under-detecting (showing 1 when there are clearly more):**
- Check the backend log for the `step.done step=diarization` line — what K did NME-SC pick? If it picked the right K but the result still shows 1, centroid-merge is collapsing. Confirm `DIARIZER_CENTROID_MERGE_THRESHOLD=0.0`.
- If NME-SC itself picked K=1, the recording's speakers might genuinely have very similar voices (same gender, same accent). Not much we can do at the embedding level without switching models.

**Over-detecting (showing many when there's clearly 1):**
- This is the tradeoff we accepted by disabling centroid-merge. For specific recordings, set `DIARIZER_CENTROID_MERGE_THRESHOLD=0.55` (catches obvious false splits) or `DIARIZER_MAX_SPEAKERS=2` as a hard cap.
- The LLM speaker-identification step also assigns names, so a single speaker split into "Speaker 1" and "Speaker 2" can be merged at the UI level by renaming.

**Phantom "Speaker N" appearing at low percentages:**
- Should be impossible after decision 12. If it happens, check that `align_transcript_with_speakers` is still using the nearest-by-midpoint fallback.
