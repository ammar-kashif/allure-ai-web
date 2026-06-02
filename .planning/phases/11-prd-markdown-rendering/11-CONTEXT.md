# Phase 11: PRD Markdown Rendering - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Render PRD content as formatted text instead of raw markdown syntax. Replace the naive line-by-line parser in PrdContent with a proper markdown rendering library. Read-only display only — no editing, no export, no new document types.

</domain>

<decisions>
## Implementation Decisions

### Rendering Approach
- Use react-markdown as the rendering library — replaces the existing 40-line custom parser entirely
- Include remark-gfm plugin for GitHub Flavored Markdown support (tables, strikethrough, task lists, autolinks)
- Include rehype-sanitize to strip raw HTML tags for defense-in-depth security
- Scope: PRD documents only — Mermaid diagram rendering (MermaidDiagram component) is unchanged

### Typography & Styling
- Use @tailwindcss/typography plugin with prose classes for consistent markdown styling
- Override prose headings to use font-heading (Space Grotesk) and body text to use Inter — matches the app's existing visual identity
- Use dark:prose-invert for dark mode support
- Keep the existing rounded-xl bg-card shadow container around the PRD content — consistent with Mermaid diagram display

### Supported Markdown Features
- Full GFM feature set: headings (h1-h4), bold, italics, ordered/unordered lists, tables, horizontal rules, blockquotes
- No syntax highlighting for code blocks — render with basic monospace styling only (PRDs rarely contain code)
- Strip images via rehype-sanitize — LLM generates text-only PRDs
- Links rendered as clickable with target="_blank" to open in new tab

### Claude's Discretion
- Exact prose modifier classes and spacing customization
- How to configure rehype-sanitize schema (which tags to allow/strip)
- react-markdown component override details for links (target="_blank")
- Tailwind typography plugin configuration in tailwind config

</decisions>

<specifics>
## Specific Ideas

- The existing PrdContent component at src/components/document/prd-content.tsx is the only file that needs replacement — the document detail page already delegates to it via `<PrdContent content={document.content} />`
- Phase 8 established PRD sections: Overview, Goals & Objectives, Functional Requirements, Non-Functional Requirements, Constraints, Open Questions — the renderer should handle all of these cleanly

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/components/document/prd-content.tsx`: Current naive parser — will be replaced with react-markdown
- `src/components/document/mermaid-diagram.tsx`: Mermaid renderer — NOT touched, stays as-is
- `src/app/(dashboard)/documents/[id]/page.tsx`: Document detail page — already conditionally renders PrdContent vs MermaidDiagram

### Established Patterns
- shadcn/ui + Tailwind CSS + oklch colors + indigo theme (Phase 2.1)
- Space Grotesk headings + Inter body text (Phase 2.1)
- Component receives content as string prop and renders it

### Integration Points
- `src/components/document/prd-content.tsx`: Replace implementation, keep same interface (`content: string` prop)
- `tailwind.config.ts`: Add @tailwindcss/typography plugin
- `package.json`: Add react-markdown, remark-gfm, rehype-sanitize, @tailwindcss/typography

</code_context>

<deferred>
## Deferred Ideas

- PDF download/export for PRD documents — future QOL phase

</deferred>

---

*Phase: 11-prd-markdown-rendering*
*Context gathered: 2026-03-26*

