# Product

## Register

product

## Users

Engineering and cross-functional product teams. Context: capturing standups, planning sessions, and discovery calls; reviewing transcripts and extracted action items between or after meetings; generating PRDs from recorded discussions. Job to be done: turn unstructured meeting audio into trustworthy, actionable artifacts (transcripts, decisions, tasks, PRDs) without manual note-taking.

## Product Purpose

Meeting intelligence platform: record, transcribe with speaker diarization, extract decisions/action items/blockers via local LLM, and produce structured PRDs. Runs locally for privacy. Success = a team trusts the output enough to skip manual minutes and works directly from generated tasks and docs.

## Brand Personality

Calm, precise, professional. Voice: factual, low-noise, no hype. Tone: confident but quiet — the tool stays out of the way so the content (transcript, outcomes, PRD) is the hero. Emotional goal: a sense of "this is reliable infrastructure" rather than "this is an exciting AI toy."

## Anti-references

- Generic AI SaaS aesthetic: purple-mesh gradient heroes, animated blobs, "sparkle" iconography, gradient-text headings, ChatGPT-clone chat shells as the primary surface.
- Heavy enterprise chrome: Jira/Confluence-style dense toolbars, boxy corporate cards, busy multi-color status pills, cluttered breadcrumbs.
- Hero-metric template: oversized number + small label + supporting stats, used decoratively.

## Design Principles

1. **Content is the hero.** Transcripts, outcomes, tasks, and PRDs get the strongest typography and the most space. Chrome (sidebar, headers, toolbars) recedes.
2. **Quiet confidence.** No gradients-for-decoration, no emoji-driven UI, no celebratory motion. State changes are honest and crisp.
3. **Density matches purpose.** Data-dense surfaces (transcripts, task lists) tighten; review surfaces (PRD, single recording) breathe. Same scale, different rhythm.
4. **One accent, used sparingly.** Indigo signals primary action, current selection, and key data. Everything else is tinted neutral.
5. **Trustworthy by default.** Reflect real state (processing, transcribing, failed) clearly; never decorate empty or pending states with hype.

## Accessibility & Inclusion

Target WCAG 2.2 AA. Keyboard-navigable across sidebar, lists, and transcript player. Respect `prefers-reduced-motion` (skip fade/scale entrance animations). Color is never the sole signal for state (pair with text/icon). Sufficient contrast in both light and dark themes — verify muted-foreground on muted backgrounds.
