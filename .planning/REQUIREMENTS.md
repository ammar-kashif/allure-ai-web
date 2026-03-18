# Requirements: Allure AI

**Defined:** 2026-03-18
**Core Value:** Recording a meeting and getting a reviewable, structured project plan with evidence links and confidence gating in under 5 minutes.

## v1.1 Requirements

Requirements for Meeting Intelligence & Document Context milestone. Each maps to roadmap phases.

### Audio Playback

- [x] **PLAY-01**: User can play/pause meeting audio from the recording detail page
- [ ] **PLAY-02**: Current utterance is highlighted during audio playback
- [x] **PLAY-03**: User can change playback speed (0.5x, 1x, 1.5x, 2x)

### Speaker Management

- [x] **SPKR-01**: User can edit speaker labels (rename "Speaker 1" to "John")
- [x] **SPKR-02**: User can assign roles to speakers (e.g., "Product Manager")
- [x] **SPKR-03**: User can view per-speaker statistics (time, words, WPM, turns, avg turn, pauses, avg pause)
- [x] **SPKR-04**: Speakers are color-coded in the transcript view

### Meeting Statistics

- [x] **MEET-01**: User can view meeting duration on the recording detail page
- [x] **MEET-02**: User can view processing time on the recording detail page
- [x] **MEET-03**: User can view number of speakers on the recording detail page
- [ ] **MEET-04**: User can view number of attached documents on the recording detail page

### Recording UX

- [x] **RUX-01**: After recording completes, a popup appears with name and project fields
- [x] **RUX-02**: User can upload reference documents in the post-recording popup
- [x] **RUX-03**: Transcription and diarization proceed in the background while popup is open

### Document Attachments

- [x] **DOC-01**: User can upload documents (PDF, DOCX) to a recording
- [x] **DOC-02**: Attached document text is extracted and stored for generation context
- [ ] **DOC-03**: Attached documents are listed on the recording detail page

### Diarization Quality

- [x] **DIAR-01**: Backend uses AgglomerativeClustering for speaker diarization
- [x] **DIAR-02**: Speaker count is auto-detected (no manual input required)

### Document Generation Quality

- [ ] **GEN-01**: Mermaid diagrams model the product discussed, not the meeting flow
- [ ] **GEN-02**: PRD and Mermaid generation uses attached document text as context
- [ ] **GEN-03**: Improved prompts produce higher-quality PRD and Mermaid output

## Future Requirements

Deferred to v1.2+. Tracked but not in current roadmap.

### Audio Playback

- **PLAY-04**: User can click a transcript line to seek audio to that timestamp

### Speaker Management

- **SPKR-05**: Speaker profiles persist across recordings (same voice = same label)

### Meeting Intelligence

- **MINT-01**: User receives in-app notifications for completed transcriptions
- **MINT-02**: Meeting summary auto-generated alongside outcomes

## Out of Scope

| Feature | Reason |
|---------|--------|
| Waveform visualization | Complexity disproportionate to value; transcript-centric UX |
| Real-time transcription | Requires streaming STT; current batch pipeline is simpler and sufficient |
| Video recording | Storage/bandwidth, not core to meeting intelligence |
| RAG/vector DB for documents | Direct context stuffing sufficient at FYP scale |
| Speaker voice fingerprinting | ML complexity too high for FYP timeline |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAY-01 | Phase 5 | Complete |
| PLAY-02 | Phase 5 | Pending |
| PLAY-03 | Phase 5 | Complete |
| SPKR-01 | Phase 6 | Complete |
| SPKR-02 | Phase 6 | Complete |
| SPKR-03 | Phase 5 | Complete |
| SPKR-04 | Phase 5 | Complete |
| MEET-01 | Phase 5 | Complete |
| MEET-02 | Phase 5 | Complete |
| MEET-03 | Phase 5 | Complete |
| MEET-04 | Phase 7 | Pending |
| RUX-01 | Phase 6 | Complete |
| RUX-02 | Phase 6 | Complete |
| RUX-03 | Phase 6 | Complete |
| DOC-01 | Phase 7 | Complete |
| DOC-02 | Phase 7 | Complete |
| DOC-03 | Phase 7 | Pending |
| DIAR-01 | Phase 5 | Complete |
| DIAR-02 | Phase 5 | Complete |
| GEN-01 | Phase 8 | Pending |
| GEN-02 | Phase 8 | Pending |
| GEN-03 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation*
