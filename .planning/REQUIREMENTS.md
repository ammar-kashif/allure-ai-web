# Requirements: Allure AI

**Defined:** 2026-03-11
**Core Value:** Recording a meeting and getting a reviewable, structured project plan with evidence links and confidence gating in under 5 minutes.

## v1 Requirements

Requirements for FYP demo. Each maps to roadmap phases.

### Recording

- [ ] **REC-01**: User can start recording with one tap from any screen (global record button)
- [ ] **REC-02**: Browser captures laptop microphone audio via Web Audio API
- [ ] **REC-03**: Recording auto-saves to filesystem with crash recovery
- [ ] **REC-04**: Recording Hub displays all recordings with status (Unassigned, Processing, Ready)
- [ ] **REC-05**: User can assign a recording to a project (create new or attach existing session)
- [ ] **REC-06**: Unassigned recordings are private to the creating user

### Transcription

- [ ] **STT-01**: Recording is sent to Python backend for Whisper STT processing
- [ ] **STT-02**: Transcript includes timestamps for each utterance
- [ ] **STT-03**: Transcript includes speaker diarization labels (Speaker 1, Speaker 2, etc.)
- [ ] **STT-04**: Processing status updates display in real-time (queued → processing → complete)

### Extraction

- [ ] **EXT-01**: AI extracts structured outcomes from transcript (decisions, action items, requirements, blockers)
- [ ] **EXT-02**: Each outcome includes title, details, confidence score, and evidence link to transcript utterance(s)
- [ ] **EXT-03**: Outcomes display grouped by type with confidence indicators
- [ ] **EXT-04**: Items below 0.80 confidence are visually flagged for review
- [ ] **EXT-05**: User can promote action items to tasks with backlinks to source evidence
- [ ] **EXT-06**: User can promote requirements to requirement records with backlinks
- [ ] **EXT-07**: Promoted tasks/requirements retain evidence links to original transcript and audio timestamp

### Task Management

- [ ] **TASK-01**: User can create, read, update, and delete tasks
- [ ] **TASK-02**: Tasks have title, status, priority, due date, assignee (optional), and tags
- [ ] **TASK-03**: Tasks display in a sortable/filterable list view
- [ ] **TASK-04**: Tasks display in a drag-and-drop Kanban board view
- [ ] **TASK-05**: Dragging a Kanban card updates task status

### Document Generation (Stretch)

- [ ] **DOC-01**: User can generate a PRD from approved outcomes and requirements (template-based)
- [ ] **DOC-02**: User can generate Mermaid diagrams (user flow flowchart, ERD) from project data
- [ ] **DOC-03**: Generated Mermaid renders without syntax errors

## v2 Requirements

Deferred to post-FYP. Tracked but not in current roadmap.

### Review Workflow

- **REV-01**: Admin review workflow with approve, edit, reject actions per outcome
- **REV-02**: Items below 0.80 cannot be marked authoritative without Admin approval
- **REV-03**: Transcript editor with edit history (editor identity and timestamp)

### Playback

- **PLAY-01**: Audio playback synced to transcript (click utterance → seek to timestamp)
- **PLAY-02**: Waveform visualization during playback

### Task Advanced

- **TASK-06**: Task dependencies (blocks/blocked-by relationships)
- **TASK-07**: Overdue tasks are automatically flagged
- **TASK-08**: Milestones with date range, status, and roll-up progress from linked tasks

### Session Enrichment

- **SESS-01**: Upload PPTX/PDF slides to a session
- **SESS-02**: Parse slide structure into browsable sections
- **SESS-03**: Alignment suggestions between transcript and slide sections with scores

### Collaboration

- **COLLAB-01**: Threaded comments on tasks, outcomes, and documents
- **COLLAB-02**: Activity log recording actor, timestamp, and change summary

### Access Control

- **AUTH-01**: Admin role with full CRUD, approve, promote, and manage permissions
- **AUTH-02**: Viewer role with read-only access to assigned projects
- **AUTH-03**: Unauthorized actions blocked and logged

### Notifications

- **NOTIF-01**: In-app notifications for task due, transcript ready, items needing review
- **NOTIF-02**: Mark as read and basic filtering

### QA Agent

- **QA-01**: QA scoring for documents with 0.80 pass threshold and actionable fix list
- **QA-02**: Documents cannot be marked Ready when QA score is below 0.80

### Integrations

- **INT-01**: CSV import/export for tasks and milestones
- **INT-02**: MCP integration with at least one tool (Notion, Jira, or Trello)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Video conferencing / calendar | Not a meeting platform — Allure records, doesn't host meetings |
| Cloud LLM for core inference | Local-first constraint for privacy/reliability |
| Enterprise features (SSO, orgs) | FYP scope — single team use case |
| Mobile app | Web-first for FYP |
| AI chat assistant | Post-FYP — use structured workflows instead |
| Dashboards / analytics | Post-FYP — list/Kanban views are sufficient |
| Real-time collaborative editing | Complexity too high for FYP timeline |
| AI-assisted project planning (auto-generate plans from prompts) | Deferred — manual task creation + promotion from outcomes is sufficient for demo |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REC-01 | Phase 1 | Pending |
| REC-02 | Phase 1 | Pending |
| REC-03 | Phase 1 | Pending |
| REC-04 | Phase 1 | Pending |
| REC-05 | Phase 1 | Pending |
| REC-06 | Phase 1 | Pending |
| STT-01 | Phase 1 | Pending |
| STT-02 | Phase 1 | Pending |
| STT-03 | Phase 1 | Pending |
| STT-04 | Phase 1 | Pending |
| EXT-01 | Phase 2 | Pending |
| EXT-02 | Phase 2 | Pending |
| EXT-03 | Phase 2 | Pending |
| EXT-04 | Phase 2 | Pending |
| EXT-05 | Phase 2 | Pending |
| EXT-06 | Phase 2 | Pending |
| EXT-07 | Phase 2 | Pending |
| TASK-01 | Phase 3 | Pending |
| TASK-02 | Phase 3 | Pending |
| TASK-03 | Phase 3 | Pending |
| TASK-04 | Phase 3 | Pending |
| TASK-05 | Phase 3 | Pending |
| DOC-01 | Phase 4 | Pending |
| DOC-02 | Phase 4 | Pending |
| DOC-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap creation*
