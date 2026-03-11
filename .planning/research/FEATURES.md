# Feature Landscape

**Domain:** AI-powered project management with meeting-to-execution workflow
**Researched:** 2026-03-11
**Overall confidence:** MEDIUM (based on training data; web verification tools unavailable)

## Competitor Landscape

Before categorizing features, here is the competitive context Allure sits within:

| Product | Core Strength | Gap Allure Fills |
|---------|--------------|------------------|
| **Otter.ai** | Real-time transcription, AI meeting summaries, action item extraction | No project management — outputs are notes, not structured plans |
| **Fireflies.ai** | Meeting transcription, topic tracking, CRM integrations, conversation intelligence | Analytics-focused; action items exist but don't promote into real task boards |
| **Grain** | Video highlight clips, shared meeting moments | Collaboration-oriented, no structured outcome extraction |
| **Fellow** | Meeting agendas, action items, 1:1 templates, integrations with Asana/Jira | Closest competitor model — but requires manual agenda setup, not AI-first extraction |
| **Linear** | Best-in-class issue tracking, cycles, roadmaps, AI triage | No meeting/transcription integration at all |
| **Notion** | Flexible docs + databases, AI writing assist, meeting notes templates | General-purpose; meeting-to-project workflow requires manual glue |
| **ClickUp** | Everything-app PM: tasks, docs, goals, whiteboards, AI | Broad but shallow AI; no native transcription pipeline |

**Key insight:** The market splits into two camps — transcription tools (Otter, Fireflies, Grain) that produce notes but stop short of project management, and PM tools (Linear, Notion, ClickUp) that have no meeting intelligence. Fellow bridges the gap but requires manual structure. Allure's differentiation is the automated pipeline: record -> transcribe -> extract structured outcomes -> promote to project artifacts, all local-first.

---

## Table Stakes

Features users expect from any tool in this space. Missing any of these and the product feels broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Audio recording** | Core input for the entire pipeline; every transcription tool has this | Low | Already in backend; frontend needs one-tap record UX |
| **Speech-to-text transcription** | Otter, Fireflies, and every competitor does this; it is the baseline | High (backend) | Whisper pipeline exists in backend; frontend needs status/progress display |
| **Speaker identification/diarization** | Otter and Fireflies both label speakers; users expect to know who said what | High (backend) | Backend handles via Whisper + pyannote; frontend shows speaker labels |
| **Transcript viewing with audio sync** | Otter pioneered click-to-seek; users expect it in any transcription UI | Medium | Click utterance to seek audio; highlight current segment during playback |
| **AI-generated meeting summary** | Every competitor (Otter, Fireflies, Notion AI, ClickUp AI) offers this now | Medium | LLM generates summary from transcript; display at top of transcript view |
| **Action item extraction** | Otter, Fireflies, Fellow all extract action items; table stakes since ~2023 | Medium | LLM extracts; must show source evidence (which utterance) |
| **Task management (list view)** | Linear, ClickUp, Notion, Fellow all have task lists; PM tools require this | Medium | CRUD tasks with status, assignee, due date, priority |
| **Search across transcripts** | Otter and Fireflies both offer full-text search; users need to find past discussions | Low-Medium | Full-text search over transcripts, filterable by project/date |
| **Basic access control** | Any multi-user tool needs Admin vs Viewer separation minimum | Low | Admin/Viewer roles per PROJECT.md |
| **Notifications** | Task due, transcript ready, items needing review — standard PM feature | Low-Medium | In-app notifications; no email/push needed for FYP |

---

## Differentiators

Features that set Allure apart. Not universally expected, but create competitive advantage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Structured outcome extraction with categories** | Goes beyond action items: extracts decisions, requirements, blockers, risks as typed entities. No competitor does all four categories with evidence links. Otter/Fireflies only do action items + summary. | High | Core differentiator. LLM extracts into Decision/ActionItem/Requirement/Blocker buckets |
| **Confidence-gated review workflow** | Items below 0.80 confidence require Admin approval before becoming authoritative. No competitor exposes extraction confidence to users. Builds trust in AI outputs. | Medium | Unique to Allure. Review queue UI where Admin accepts/rejects/edits extractions |
| **Evidence backlinks (outcome -> transcript moment)** | Every extracted outcome links back to the exact utterance(s) that generated it. Click to hear the original context. Fellow has loose note links; nobody has utterance-level evidence chains. | Medium | Click an action item, jump to the 30-second audio clip where it was discussed |
| **Outcome promotion to project artifacts** | Approved outcomes directly become tasks, requirements docs, risk entries — not copy-paste. The pipeline continues past extraction into project structure. Fireflies stops at notes; this goes to execution. | Medium | "Promote" button on reviewed outcomes creates linked task/requirement/risk entry |
| **AI-generated project plans from outcomes** | Feed approved outcomes to LLM to generate task breakdown, milestones, dependencies. No transcription tool does this. Linear/ClickUp have AI task generation but not from meeting transcripts. | High | Generate milestone + task tree from a set of approved outcomes |
| **PRD generation from approved requirements** | Template-based document generation from structured requirement outcomes. Turns meeting discussions into formal project requirement documents automatically. | Medium | LLM fills PRD template from extracted requirements; export as document |
| **Diagram generation (Mermaid)** | Auto-generate user flow, ERD, or architecture diagrams from project data. Visual output from verbal meetings. | Medium | Mermaid rendering from LLM output; limited to supported diagram types |
| **Local-first / privacy-first** | All inference runs on-device (Whisper + llama.cpp). No cloud LLM. Strong differentiator for privacy-sensitive users and academic settings. | Low (architecture) | Already decided; highlight in positioning |
| **Slide/doc alignment with transcript** | Upload PPTX/PDF and align slides to transcript segments. Know what was being discussed when each slide was shown. No competitor does this. | High | Requires time-alignment heuristics; strong FYP demo feature |
| **QA agent for completeness scoring** | Automated check: are all action items assigned? Are requirements complete? Consistency scoring on the project plan. No competitor offers this. | Medium-High | LLM-based review pass; unique to Allure |

---

## Anti-Features

Features to deliberately NOT build. Either out of scope, strategically wrong, or complexity traps.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Video conferencing / calendar integration** | Allure is not a meeting platform. Zoom/Teams/Meet own this space. Building even basic video adds months of complexity for zero differentiation. | Record audio locally. Import recordings from other tools later (post-FYP). |
| **Real-time live transcription during meetings** | Requires streaming STT, low-latency processing, live UI updates. Otter's core product took years to polish. Post-recording batch processing is reliable and achievable in 2 weeks. | Process after recording stops. Show processing status. |
| **AI chat assistant / conversational interface** | ChatGPT-style interfaces are generic and hard to make good. Structured workflows (extract -> review -> promote) are more trustworthy and demable than open-ended chat. | Use structured extraction + review workflows per PROJECT.md |
| **Enterprise features (SSO, SCIM, org hierarchy)** | FYP scope. 2-3 users. Enterprise auth is weeks of work with zero demo value. | Admin/Viewer roles only. Hardcoded users or simple auth. |
| **Mobile app** | Native mobile is a separate project. Web works on mobile browsers if needed. | Responsive web design for tablet if time permits; desktop-first. |
| **Advanced analytics / dashboards** | ClickUp and Monday.com territory. Reporting is deep work with low demo impact. Charts don't prove the core thesis. | Show milestone progress roll-up and task completion counts. No custom dashboards. |
| **Third-party integrations (Slack, Jira, Asana)** | Each integration is days of work. No FYP evaluator will test Jira integration. | Build clean internal APIs. Integrations are a post-FYP growth feature. |
| **Collaborative real-time editing** | Google Docs-style multiplayer editing is extremely complex (CRDTs, OT). Single-user edit with conflict prevention is sufficient. | Lock-based editing or last-write-wins for FYP scope. |
| **Email notifications** | Requires email service setup, deliverability, templates. Zero value for FYP demo. | In-app notifications only. |
| **Custom workflow automation** | Zapier-style "when X then Y" is scope creep. The pipeline IS the workflow. | Hardcoded pipeline: Record -> Transcribe -> Extract -> Review -> Promote. |

---

## Feature Dependencies

```
Audio Recording
  --> Transcription (STT)
    --> Speaker Diarization (concurrent with STT)
    --> Transcript Viewer with Audio Sync
      --> Full-text Search
    --> AI Meeting Summary
    --> Outcome Extraction (decisions, action items, requirements, blockers)
      --> Confidence Scoring
        --> Confidence-Gated Review Workflow
          --> Outcome Promotion to Tasks/Requirements/Risks
            --> Task Management (list + Kanban)
              --> Task Dependencies
              --> Milestone Roll-up
            --> AI Project Plan Generation
            --> PRD Generation
            --> Diagram Generation
      --> Evidence Backlinks (outcome -> utterance)

Slide/Doc Upload (independent input)
  --> Transcript-to-Slide Alignment (requires transcript)

Access Control (independent, needed early)
Notifications (depends on: tasks, transcripts, review workflow)
QA Agent (depends on: tasks, requirements, milestones existing)
```

---

## MVP Recommendation

Given the 2-week FYP constraint and core demo path (Record -> Transcribe -> Extract -> Promote -> Manage), prioritize in this order:

### Must Ship (Core Demo Path)

1. **Audio recording** — one-tap UX, the entry point
2. **Transcription display with speaker labels** — show the STT pipeline works
3. **Audio-synced transcript viewer** — click-to-seek proves quality
4. **Outcome extraction with evidence links** — THE differentiator; show categorized extraction
5. **Confidence-gated review workflow** — shows the human-in-the-loop trust mechanism
6. **Outcome promotion to tasks** — completes the pipeline from meeting to execution
7. **Basic task management (list view)** — prove the outputs are actionable

### Should Ship (Demo Polish)

8. **AI meeting summary** — low effort, high visual impact at top of transcript
9. **Milestone view with roll-up** — shows project-level planning
10. **AI project plan generation** — impressive demo moment: "generate a plan from this meeting"
11. **Kanban view for tasks** — visual polish, familiar UX

### Stretch Goals

12. **PRD generation** — great demo but not on the critical path
13. **Slide/doc alignment** — unique feature, but complex; only if time permits
14. **Diagram generation (Mermaid)** — visually impressive but optional
15. **QA agent** — sophisticated but least essential for core demo
16. **Search across transcripts** — useful but not demo-critical with few recordings

### Explicitly Defer

- Notifications (nice polish but not demo-critical)
- Access control beyond basic auth (hardcode Admin for demo)
- Any anti-feature listed above

---

## Competitive Feature Matrix

| Feature | Otter.ai | Fireflies | Fellow | Linear | Notion | ClickUp | **Allure** |
|---------|----------|-----------|--------|--------|--------|---------|------------|
| Audio recording | Yes | Bot joins calls | No | No | No | No | **Yes (local)** |
| Transcription | Yes | Yes | No | No | No | No | **Yes (Whisper)** |
| Speaker diarization | Yes | Yes | No | No | No | No | **Yes** |
| AI summary | Yes | Yes | Partial | No | Yes (AI) | Yes (AI) | **Yes** |
| Action item extraction | Yes | Yes | Manual | No | No | No | **Yes (auto)** |
| Decision extraction | No | No | No | No | No | No | **Yes** |
| Requirement extraction | No | No | No | No | No | No | **Yes** |
| Blocker extraction | No | No | No | No | No | No | **Yes** |
| Confidence scoring | No | No | No | No | No | No | **Yes** |
| Evidence backlinks | No | Partial | No | No | No | No | **Yes** |
| Task management | No | No | Partial | Yes | Yes | Yes | **Yes** |
| Project planning from meetings | No | No | No | No | No | No | **Yes** |
| PRD generation | No | No | No | No | No | No | **Yes** |
| Local/private inference | No | No | No | No | No | No | **Yes** |

---

## Sources

- Otter.ai product knowledge (training data, MEDIUM confidence)
- Fireflies.ai product knowledge (training data, MEDIUM confidence)
- Fellow.app product knowledge (training data, MEDIUM confidence)
- Linear product knowledge (training data, MEDIUM confidence)
- Notion AI product knowledge (training data, MEDIUM confidence)
- ClickUp AI product knowledge (training data, MEDIUM confidence)
- Grain product knowledge (training data, LOW confidence — less coverage in training)

**Note:** Web search and fetch tools were unavailable during this research session. All competitive analysis is based on training data (cutoff ~early 2025). Feature sets of competitors may have evolved. Confidence is MEDIUM overall — the broad feature categories are stable, but specific capabilities may have been added or changed.
