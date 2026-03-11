# Research Summary: Allure AI

**Domain:** AI-powered project management with meeting transcription (local-first)
**Researched:** 2026-03-11
**Overall confidence:** MEDIUM (all tools except Read/Write/Glob were unavailable; recommendations based on training data through early 2025; ecosystem choices are high confidence but exact version numbers should be verified via npm)

## Executive Summary

Allure is a local-first AI meeting intelligence tool that bridges two market gaps: transcription tools (Otter, Fireflies) stop at notes but never create project plans, and PM tools (Linear, Notion, ClickUp) have no meeting intelligence. Allure's pipeline -- Record, Transcribe, Extract structured outcomes, Review with confidence gating, Promote to tasks -- is unique and demonstrable.

The recommended stack is Next.js 15 (App Router) + shadcn/ui + Tailwind CSS for the frontend, communicating via REST proxy to the existing Python FastAPI backend. TanStack Query manages all server state with polling for async operations (STT and LLM inference). Zustand handles minimal UI state. dnd-kit powers the Kanban board, wavesurfer.js provides audio waveform playback synced with transcripts.

The architecture is intentionally simple: two processes (Next.js dev server + FastAPI), SQLite on disk, filesystem for audio. No message queues, no containers, no microservices. Every AI operation (Whisper STT, llama.cpp extraction) is async with status polling -- the frontend never blocks waiting for inference.

The biggest risks are not technical but operational: scope creep across 16+ features when only 7 are on the core demo path, unreliable structured output from quantized local LLMs, and late frontend-backend integration. The 2-week timeline demands brutal prioritization of the Record-to-Tasks pipeline over secondary features like PRD generation, Mermaid diagrams, and QA agents.

## Key Findings

**Stack:** Next.js 15 + React 19 + shadcn/ui + Tailwind 4 + TanStack Query v5 + Zustand + dnd-kit + wavesurfer.js. Native fetch (no axios). TypeScript types generated from FastAPI's OpenAPI spec.

**Architecture:** Two-process pipeline architecture. Frontend is a thin orchestration layer over REST. All AI inference in backend. Async job pattern with status polling for all long-running operations.

**Critical pitfall:** Local LLM (8B quantized) structured extraction is unreliable without GBNF grammar constraints. Malformed JSON and hallucinated outcomes will break the entire value chain. Must validate extraction quality by day 4-5.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation + Pipeline Integration** - Get the core pipeline working end-to-end
   - Addresses: Recording, upload, transcript display, audio sync
   - Avoids: Scope creep (Pitfall 4), late integration (Pitfall 5)
   - Rationale: Everything downstream depends on recordings flowing through STT. Prove this works on day 1-2.

2. **AI Extraction + Review** - The differentiator feature set
   - Addresses: Outcome extraction, confidence display, review workflow, evidence backlinks
   - Avoids: Unreliable LLM output (Pitfall 3), overengineered review UI (Pitfall 9)
   - Rationale: This is what makes Allure unique. Must work before building PM features.

3. **Task Management + Promotion** - Complete the pipeline into actionable outputs
   - Addresses: Task CRUD, list view, Kanban, outcome promotion with backlinks
   - Avoids: Building PM features before having data to populate them
   - Rationale: Tasks are the pipeline output. Promotion connects extraction to project management.

4. **Document Generation + Polish** - Stretch goals and demo preparation
   - Addresses: PRD generation, Mermaid diagrams, AI plan generation, notifications
   - Avoids: Touching secondary features before core path is solid
   - Rationale: These are impressive demos but only if the core pipeline works. Build only if time permits.

5. **Demo Preparation** - Fallback data, practice runs, hardware testing
   - Addresses: Pre-processed demo recordings, fallback transcripts, llama.cpp verification on demo hardware
   - Avoids: Live processing failures on demo day (Pitfall 2, Pitfall 10)
   - Rationale: 2 days of buffer for fires. There will be fires.

**Phase ordering rationale:**
- Pipeline dependencies enforce the order: recording -> transcript -> extraction -> tasks. You cannot build downstream without upstream data.
- Integration must happen in Phase 1, not Phase 3. The existing backend dictates API contracts.
- Task CRUD can be parallelized with Phase 2 (both team members working simultaneously) since it is standard CRUD UI.
- Document generation is explicitly last because it is not on the core demo path.

**Research flags for phases:**
- Phase 1: Needs integration research -- read the existing backend code to understand actual API contracts, endpoint shapes, and processing pipeline
- Phase 2: Needs prompt engineering research -- LLM extraction prompts for structured output with GBNF grammars need iterative testing
- Phase 3: Standard patterns, unlikely to need additional research (CRUD + Kanban are well-understood)
- Phase 4: Low priority research -- PRD template design and Mermaid syntax are straightforward

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Ecosystem choices (Next.js, shadcn, TanStack Query, etc.) are well-established and HIGH confidence. Exact version numbers are MEDIUM -- based on training data, may be 1-2 minor versions behind current. |
| Features | MEDIUM | Competitive landscape analysis based on training data (early 2025). Competitors may have added features since then. Core feature categorization (table stakes vs differentiators) is sound. |
| Architecture | HIGH | Two-process pipeline architecture with async jobs is a well-established pattern for local AI inference systems. No novel architectural risks. |
| Pitfalls | HIGH | The identified pitfalls (browser audio recording, LLM reliability, scope creep, late integration) are consistently reported across similar projects. These are real, recurring problems. |

## Gaps to Address

- **Existing backend API contracts:** Must read the actual FastAPI route definitions in github.com/ZainAbbas97/allure-ai before writing any frontend API hooks. The research assumes a REST contract shape that may not match reality.
- **llama.cpp GBNF grammar support:** Need to verify current state of grammar-constrained generation in the version of llama.cpp used by the backend. This is critical for reliable extraction.
- **Whisper model speed benchmarks:** Need to benchmark actual transcription speed on the team's M3 hardware with the chosen Whisper model size. This determines whether the "5 minutes" promise is achievable.
- **shadcn/ui sidebar component:** The existing sidebar component from shadcn should be evaluated for Allure's navigation needs. May need customization.
- **Exact latest package versions:** All npm package versions should be verified via `npm view [package] version` before project initialization. Training data versions may be 1-3 minor versions behind.
