# Technology Stack

**Project:** Allure AI -- AI-Powered Project Manager with Meeting Transcription
**Researched:** 2026-03-11
**Overall Confidence:** MEDIUM (versions unverified against live registries -- WebSearch/Bash/WebFetch unavailable during research. Ecosystem choices are HIGH confidence from training data through early 2025; exact latest patch versions may differ.)

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Next.js | ^15.1 | Full-stack React framework | App Router is stable and mature; Server Components reduce client JS bundle; API routes can proxy to FastAPI backend; file-based routing speeds up development in a 2-week sprint | MEDIUM |
| React | ^19.0 | UI library | Ships with Next.js 15; use() hook and Server Components are production-ready; largest ecosystem for component libraries | MEDIUM |
| TypeScript | ^5.7 | Type safety | Non-negotiable for any serious project; catches integration bugs between frontend and backend API contracts early | MEDIUM |

### UI & Styling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Tailwind CSS | ^4.0 | Utility-first CSS | v4 ships with Next.js 15 out of the box; fastest way to build custom UI in a sprint; no context-switching to CSS files | MEDIUM |
| shadcn/ui | latest (CLI) | Component library | Not an npm package -- copy-paste components built on Radix UI primitives. Full control, no version lock-in, accessible by default. Has Dialog, Sheet, Table, Tabs, Command, Toast -- covers 90% of Allure's UI needs | HIGH |
| Radix UI | (via shadcn) | Accessible primitives | Headless, composable, WAI-ARIA compliant. shadcn wraps these so you rarely import Radix directly | HIGH |
| Lucide React | ^0.460 | Icons | Default icon set for shadcn/ui; tree-shakeable; consistent style | MEDIUM |
| class-variance-authority | ^0.7 | Variant styling | Used by shadcn for component variants (size, color, state). Already included when you init shadcn | HIGH |
| tailwind-merge | ^2.6 | Class merging | Prevents Tailwind class conflicts when composing component props. Part of shadcn's cn() utility | HIGH |
| clsx | ^2.1 | Conditional classes | Lightweight conditional class builder, paired with tailwind-merge in cn() | HIGH |

### State Management & Data Fetching

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| TanStack Query (React Query) | ^5.62 | Server state / API calls | Handles caching, refetching, optimistic updates, loading/error states. Perfect for fetching transcripts, tasks, outcomes from FastAPI. Eliminates manual useEffect + useState fetch patterns | HIGH |
| Zustand | ^5.0 | Client state | Lightweight (1KB), no boilerplate, works with React 19. Use for UI state only: sidebar open/closed, current recording state, audio playback position. Do NOT put server data here -- that's TanStack Query's job | HIGH |

### Kanban / Drag-and-Drop

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| @dnd-kit/core | ^6.3 | Drag-and-drop engine | Purpose-built for React; supports keyboard/screen-reader DnD; modular (only import what you need). Best DnD library for React as of 2025 | HIGH |
| @dnd-kit/sortable | ^10.0 | Sortable lists | Extension for dnd-kit; handles Kanban column reordering and card sorting | HIGH |
| @dnd-kit/utilities | ^3.2 | DnD helpers | CSS transform utilities for smooth drag animations | HIGH |

### Audio Playback & Recording

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| wavesurfer.js | ^7.8 | Audio waveform + playback | Visual waveform display synced with transcript; supports click-to-seek which maps directly to Allure's "click utterance, seek audio" requirement; Web Audio API under the hood | HIGH |
| MediaRecorder API | (browser native) | Audio recording | Built into all modern browsers; no library needed. Record to WebM/Opus, then send chunks to backend for Whisper processing | HIGH |

### Forms & Validation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Zod | ^3.24 | Schema validation | Single schema validates both client forms and API response shapes. TypeScript-first, composable, great error messages | HIGH |
| React Hook Form | ^7.54 | Form management | Minimal re-renders, integrates with Zod via @hookform/resolvers. Use for task creation, outcome editing, PRD templates | HIGH |
| @hookform/resolvers | ^3.9 | RHF + Zod bridge | Connects Zod schemas to React Hook Form validation | HIGH |

### Markdown & Document Generation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| react-markdown | ^9.0 | Markdown rendering | Render PRDs, meeting notes, outcome summaries. Supports remark/rehype plugins | HIGH |
| mermaid | ^11.4 | Diagram rendering | Render ERDs and user flow diagrams generated by LLM. Client-side SVG rendering, no server needed | MEDIUM |

### Data Tables & Lists

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| @tanstack/react-table | ^8.20 | Headless table | Task lists, transcript tables, outcome review tables. Headless = full styling control with Tailwind. Sorting, filtering, pagination built in | HIGH |

### Notifications & Toasts

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Sonner | ^1.7 | Toast notifications | Best toast library for React as of 2025. Beautiful defaults, stacking, promise toasts for async operations. shadcn has a Sonner wrapper component | HIGH |

### URL State & Routing Helpers

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| nuqs | ^2.2 | URL search params state | Type-safe URL state management for Next.js App Router. Use for filter/sort state in task lists and Kanban views so URLs are shareable | MEDIUM |

### Date/Time

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| date-fns | ^4.1 | Date formatting | Tree-shakeable, immutable, no Moment.js bloat. Format due dates, recording timestamps, transcript timecodes | HIGH |

### HTTP Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Native fetch | (built-in) | API calls | Next.js extends fetch with caching/revalidation semantics. Do NOT add axios -- fetch is sufficient and integrates with Next.js caching layer. TanStack Query wraps fetch calls | HIGH |

### Development & Quality

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ESLint | ^9.15 | Linting | Flat config format in v9. Next.js ships eslint-config-next. Add @typescript-eslint for TS rules | MEDIUM |
| Prettier | ^3.4 | Formatting | End formatting debates. Use prettier-plugin-tailwindcss to auto-sort Tailwind classes | MEDIUM |
| prettier-plugin-tailwindcss | ^0.6 | Tailwind class sorting | Automatic consistent class ordering | MEDIUM |

### Backend (Existing -- Reference Only)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.11+ | Backend runtime | Already chosen in existing repo | HIGH |
| FastAPI | ^0.115 | API framework | Already in existing backend; async, fast, auto-generates OpenAPI spec which we can use to type the frontend | HIGH |
| Whisper | (via faster-whisper) | STT | Already built in backend pipeline | HIGH |
| llama.cpp | (Python bindings) | LLM inference | Local inference on M3 Metal; already chosen | HIGH |
| SQLite | 3.x | Database | Already chosen; accessed via backend only -- frontend never touches DB directly | HIGH |

## API Contract Strategy

The frontend communicates with FastAPI exclusively via REST. Key pattern:

1. **Generate TypeScript types from FastAPI's OpenAPI spec.** Use `openapi-typescript` (^7.4) to auto-generate types from `http://localhost:8000/openapi.json`. This eliminates manual type duplication.
2. **TanStack Query wraps all API calls.** Custom hooks like `useTranscripts()`, `useTasks()`, `useOutcomes()` encapsulate fetch + caching + error handling.
3. **Zod validates API responses** at runtime as a safety net beyond TypeScript compile-time checks.

```bash
# Generate types from running FastAPI server
npx openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.d.ts
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Framework | Next.js 15 | Vite + React | Need SSR for SEO? No. But Next.js gives file routing, API routes for proxying, and the team specified it. Vite would work but adds routing/layout boilerplate |
| State (server) | TanStack Query | SWR | TanStack Query has better devtools, mutation support, query invalidation, and optimistic updates. SWR is simpler but Allure needs the advanced features |
| State (client) | Zustand | Redux Toolkit | Redux is overkill. Allure's client state is small (UI toggles, playback state). Zustand is 1KB, zero boilerplate |
| State (client) | Zustand | Jotai | Jotai's atomic model is great for complex derived state. Allure's client state doesn't need that -- Zustand's single-store model is simpler |
| Components | shadcn/ui | Chakra UI | Chakra ships runtime CSS-in-JS (performance cost) and is an opaque dependency. shadcn gives you the source code -- you own it, modify it, no version upgrade surprises |
| Components | shadcn/ui | Material UI (MUI) | MUI is heavy (~100KB+), has its own design system that fights customization, and uses Emotion CSS-in-JS. Wrong fit for Tailwind-first projects |
| DnD | dnd-kit | react-beautiful-dnd | react-beautiful-dnd is deprecated/unmaintained by Atlassian. dnd-kit is the successor the community adopted |
| DnD | dnd-kit | @hello-pangea/dnd | Fork of react-beautiful-dnd. Maintained but dnd-kit has better architecture (hooks-based, modular, accessible) |
| Audio | wavesurfer.js | Howler.js | Howler is audio-only (no waveform visualization). Allure needs visual waveforms synced with transcript |
| Tables | TanStack Table | AG Grid | AG Grid is enterprise-grade overkill. TanStack Table is headless (Tailwind-friendly) and free |
| HTTP | Native fetch | Axios | Axios adds 13KB for features Next.js fetch already has. Interceptors? Use TanStack Query's global error handler instead |
| Forms | React Hook Form | Formik | Formik causes unnecessary re-renders and is less actively maintained. RHF is the standard choice in 2025 |
| Dates | date-fns | dayjs | Both work. date-fns is tree-shakeable by default and has a larger function library. Marginal difference |
| Markdown | react-markdown | MDX | MDX is for authoring content with components. Allure renders LLM-generated markdown -- react-markdown is the right tool |
| Toasts | Sonner | react-hot-toast | Sonner has better defaults, stacking behavior, and promise toast support. Both are tiny |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| **Axios** | Unnecessary with native fetch + TanStack Query. Adds bundle size for no benefit in Next.js |
| **Redux / Redux Toolkit** | Massive boilerplate for what Allure needs. The "server state" (tasks, transcripts) belongs in TanStack Query, not Redux |
| **CSS Modules** | Slower to write than Tailwind utilities. Allure has 2 weeks -- Tailwind is faster |
| **Styled Components / Emotion** | Runtime CSS-in-JS has performance cost and doesn't work with React Server Components |
| **Moment.js** | Massive, mutable, deprecated. Use date-fns |
| **Next-Auth / Auth.js** | Allure is local-first with simple Admin/Viewer roles. A full auth library is overkill. Use a lightweight session approach or simple token-based auth from FastAPI |
| **Prisma / Drizzle** | Database is SQLite accessed by the Python backend. Frontend should never touch the DB. All data flows through FastAPI REST endpoints |
| **tRPC** | Designed for TypeScript backends. Allure's backend is Python/FastAPI. Use OpenAPI types instead |
| **Socket.io** | Allure doesn't need real-time collaboration. Polling via TanStack Query (refetchInterval) handles transcript status updates. SSE from FastAPI is sufficient for long-running tasks if needed |
| **Electron / Tauri** | Allure is web-first per project constraints. Desktop wrapper is out of scope for FYP |
| **Storybook** | 2-week sprint. No time for component documentation. Build the product |

## Installation

```bash
# Initialize Next.js project
npx create-next-app@latest allure-frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Initialize shadcn/ui
npx shadcn@latest init

# Add shadcn components (add as needed)
npx shadcn@latest add button card dialog dropdown-menu input label select separator sheet sidebar table tabs textarea toast badge command popover scroll-area

# Core dependencies
npm install @tanstack/react-query @tanstack/react-table zustand zod react-hook-form @hookform/resolvers

# DnD for Kanban
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities

# Audio
npm install wavesurfer.js

# Markdown & diagrams
npm install react-markdown mermaid

# Utilities
npm install date-fns nuqs sonner lucide-react

# Dev dependencies
npm install -D openapi-typescript prettier prettier-plugin-tailwindcss @types/node
```

## Project Structure (Recommended)

```
src/
  app/                          # Next.js App Router
    (dashboard)/                # Route group for main app layout
      layout.tsx                # Sidebar + header layout
      page.tsx                  # Dashboard home
      recordings/
        page.tsx                # Recording Hub
        [id]/page.tsx           # Single recording view
      projects/
        page.tsx                # Project list
        [id]/
          page.tsx              # Project overview
          tasks/page.tsx        # Task list + Kanban
          outcomes/page.tsx     # Outcome review
          prd/page.tsx          # PRD viewer
      transcripts/
        [id]/page.tsx           # Transcript editor + audio sync
    api/                        # Next.js API routes (proxy to FastAPI)
      [...proxy]/route.ts       # Catch-all proxy to FastAPI
  components/
    ui/                         # shadcn components (auto-generated)
    recording/                  # Recording-specific components
    transcript/                 # Transcript editor components
    kanban/                     # Kanban board components
    outcomes/                   # Outcome review components
  hooks/                        # Custom React hooks
    use-recordings.ts           # TanStack Query hooks for recordings
    use-tasks.ts                # TanStack Query hooks for tasks
    use-audio-recorder.ts       # MediaRecorder wrapper
  lib/
    api/
      client.ts                 # Fetch wrapper with base URL
      schema.d.ts               # Auto-generated from OpenAPI
    utils.ts                    # cn() and helpers
  stores/
    ui-store.ts                 # Zustand: sidebar, modals, playback
```

## Key Architecture Decisions for the Stack

1. **No ORM on the frontend.** All data flows through FastAPI REST. The frontend is a pure API consumer.
2. **Server Components for data-heavy pages.** Transcript lists, task tables, project overviews fetch data on the server. Interactive parts (Kanban, audio player, recording) are Client Components.
3. **API proxy through Next.js API routes.** Frontend calls `/api/recordings` which proxies to `http://localhost:8000/recordings`. This avoids CORS issues and gives a single origin.
4. **OpenAPI-generated types.** Run `openapi-typescript` against FastAPI's auto-generated spec. Single source of truth for API contracts.
5. **Zustand for UI state only.** Recording in-progress, playback position, sidebar state. Never for server data.
6. **TanStack Query for all server data.** Tasks, recordings, transcripts, outcomes, projects. Caching, refetching, optimistic updates all handled.

## Sources

- Next.js documentation (nextjs.org/docs) -- App Router, Server Components, fetch caching
- shadcn/ui documentation (ui.shadcn.com) -- Component installation, theming
- TanStack Query documentation (tanstack.com/query) -- v5 API, query invalidation patterns
- dnd-kit documentation (dndkit.com) -- Sortable preset for Kanban
- wavesurfer.js documentation (wavesurfer.js.org) -- v7 Web Audio API integration
- Zustand GitHub (github.com/pmndrs/zustand) -- v5 with React 19 support
- openapi-typescript GitHub (github.com/openapi-ts/openapi-typescript) -- Type generation from OpenAPI

**Note:** All version numbers are based on training data through early 2025. Exact latest patch versions should be verified via `npm view [package] version` before installation. The ecosystem choices and rationale are HIGH confidence regardless of minor version differences.
