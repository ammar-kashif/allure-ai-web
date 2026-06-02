---
name: Allure AI
description: Quiet, document-grade interface for a local meeting intelligence platform.
colors:
  primary: "#3b51d4"
  primary-foreground: "#fafafa"
  background: "#fcfcfd"
  foreground: "#1a1c26"
  card: "#ffffff"
  card-foreground: "#1a1c26"
  muted: "#f3f3f7"
  muted-foreground: "#6a6d7e"
  accent: "#e3e3f4"
  accent-foreground: "#3a3c87"
  secondary: "#f1f1f5"
  secondary-foreground: "#3a3c5a"
  border: "#e3e3eb"
  input: "#e3e3eb"
  destructive: "#d63a2c"
  ring: "#3b51d4"
typography:
  display:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.005em"
rounded:
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "14px"
  "2xl": "18px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  "2xl": "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.lg}"
    height: "32px"
    padding: "0 10px"
  button-primary-hover:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
  button-outline:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
    height: "32px"
    padding: "0 10px"
  button-outline-hover:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.foreground}"
  button-ghost:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
    height: "32px"
    padding: "0 10px"
  button-destructive:
    backgroundColor: "{colors.destructive}"
    textColor: "{colors.background}"
    rounded: "{rounded.lg}"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-foreground}"
    rounded: "{rounded.xl}"
    padding: "16px"
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
    height: "36px"
    padding: "0 12px"
  badge-default:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.pill}"
    height: "20px"
    padding: "0 8px"
  badge-outline:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.pill}"
    height: "20px"
    padding: "0 8px"
---

# Design System: Allure AI

## 1. Overview

**Creative North Star: "The Quiet Operator"**

Allure AI is a working surface for engineering and product teams to turn raw meeting audio into trustworthy artifacts. The interface is infrastructure: it carries the content (transcripts, outcomes, tasks, PRDs) without competing with it. Chrome recedes. The single indigo accent does one job, signal, and it does that job rarely. Everything else is a tinted neutral.

The system is built around restraint. Density flexes with purpose: dense for transcript lists and task tables; airy for PRDs and single-recording reviews. Motion is honest, an `ease-out` decay that confirms a state change happened, never choreography that asks for attention. Cards exist where containment is structural, never as decoration; nothing is wrapped in a card because "a card looked nice."

What this system explicitly rejects: purple-mesh gradient heroes, sparkle iconography, gradient-clipped headings, ChatGPT-clone chat shells, Jira-style toolbars, boxy enterprise chrome, hero-metric SaaS templates.

**Key Characteristics:**
- Content is the hero; chrome is supporting cast.
- Indigo is rare, intentional, and singular in role.
- Type carries hierarchy more than color or size variance does.
- Spacing scales with viewport via `clamp()`; density varies by surface, not by mood.
- Motion confirms, never performs.

## 2. Colors

A single saturated indigo (the brand voice) sits atop a cool-tinted neutral field. Every neutral carries a trace of the indigo hue family (chroma 0.005-0.01), so nothing reads as gray office paper.

### Primary
- **Signal Indigo** (`oklch(0.55 0.22 265)` / `#3b51d4`): The only saturated color in the system. Used for primary action, active selection, focus rings, and live data accents. Never decorative. Never as a hero background.

### Neutral
- **Page Field** (`oklch(0.995 0.002 265)` / `#fcfcfd`): The base background. A breath of indigo in an off-white sheet.
- **Card Sheet** (`#ffffff`): Card and popover surface. The one place pure white is permitted, because it sits *on* the field, not in the room.
- **Ink** (`oklch(0.15 0.01 265)` / `#1a1c26`): Body text and headings. Deep slate, not black.
- **Muted Field** (`oklch(0.965 0.005 265)` / `#f3f3f7`): Hover states, secondary surfaces, table-row alternations.
- **Muted Voice** (`oklch(0.50 0.02 265)` / `#6a6d7e`): Captions, metadata, timestamps, hint copy.
- **Hairline** (`oklch(0.91 0.01 265)` / `#e3e3eb`): Borders, inputs, dividers. Used 60% opacity (`border-border/60`) in chrome contexts so it disappears further.
- **Accent Tint** (`oklch(0.94 0.03 265)` / `#e3e3f4`): Selected nav item, soft callouts. Carries the indigo trace at low chroma.

### Semantic
- **Alarm Red** (`oklch(0.577 0.245 27.325)` / `#d63a2c`): Destructive actions and transcription errors only. Never for warnings or "attention" badges.

### Named Rules
**The One Voice Rule.** Signal Indigo is used on no more than 10% of any screen. Its rarity is what makes it readable as signal. If two indigo elements are competing for attention on the same surface, one of them is wrong.

**The Tinted Neutral Rule.** No `#000`, no `#fff`, with the single exception of `card` (the sheet-on-paper metaphor). Every other neutral carries chroma 0.005-0.01 toward hue 265.

**The Color-Plus-Text Rule.** Color is never the only signal for state. A red badge always pairs with text or icon; an indigo selection always pairs with a position or label.

## 3. Typography

**Display Font:** Space Grotesk (with `ui-sans-serif, system-ui, sans-serif` fallback)
**Body Font:** Inter (with `ui-sans-serif, system-ui, sans-serif` fallback)

**Character:** Space Grotesk gives headings a precise, drafted feel without leaning technical. Inter handles the running text with the neutrality of a clean operations log. Together they read as "structured document, not marketing site."

### Hierarchy
- **Display** (Space Grotesk, 700, `1.75rem`/28px, `tracking: -0.02em`, line-height 1.15): Page titles only ("Dashboard", "Recordings", document titles). One per page.
- **Headline** (Space Grotesk, 600, `1.25rem`/20px, `tracking: -0.01em`): Section heads inside a page (Speaker Stats, Recording Info).
- **Title** (Space Grotesk, 600, `1rem`/16px): Card and panel titles. Quiet enough to sit next to body copy without out-shouting it.
- **Body** (Inter, 400, `0.9375rem`/15px, `line-height: 1.55`): Running text. Capped at 72ch in prose surfaces (PRD content). Default text size in detail pages.
- **Label** (Inter, 500, `0.8125rem`/13px): Metadata, table headers, timestamps, captions. Never uppercase. Spaced `0.005em` for a slight measured rhythm.

### Named Rules
**The 72ch Rule.** Prose surfaces (PRD body, generated documents) cap at 72ch and center. Wide monitors get margin, not stretched text.

**The Heading-Carries-Hierarchy Rule.** Hierarchy comes from family + weight contrast, not color shifts. Headings stay `foreground`; section heads stay `foreground`; titles stay `foreground`. Indigo never colors a heading.

**The No-Uppercase-Labels Rule.** Labels read as plain prose-cased text. No `text-transform: uppercase` on UI copy. Uppercase belongs to print, not operations tooling.

## 4. Elevation

Layered ambient. The system uses compound shadows (`shadow-card`) on cards, with a paired `shadow-card-hover` that lifts cards by 2-4px of perceived elevation on interaction. Shadows are diffuse and low-contrast in light mode; in dark mode they carry through with proportionally darker blurs. Depth is real but never theatrical.

### Shadow Vocabulary
- **xs** (`0 1px 2px rgba(0,0,0,0.04)`): Input chrome. Subliminal.
- **sm** (`0 2px 8px rgba(0,0,0,0.06)`): Sticky headers and tooltips.
- **md** (`0 4px 16px rgba(0,0,0,0.08)`): Popovers, dropdowns.
- **lg** (`0 8px 32px rgba(0,0,0,0.10)`): Sheets and side panels.
- **xl** (`0 16px 48px rgba(0,0,0,0.12)`): Dialogs.
- **card** (compound, three layers including a hairline ring): The default card resting state.
- **card-hover** (compound, lifted): Card hover state. Combine with `transform: translateY(-1px)` only on interactive cards, never on static cards.
- **focus** (`0 0 0 3px rgba(primary, 0.15)`): Keyboard focus ring on all interactive primitives.

### Named Rules
**The Hairline-Plus-Shadow Rule.** Cards always carry both a low-contrast hairline ring (`inset 0 0 0 1px`) and a soft ambient shadow. Either alone reads as cheap; together they read as "real paper on the field."

**The No-Decorative-Shadow Rule.** Shadows exist to communicate elevation or focus. A shadow on a hero block, on a `<section>` background, or on text is wrong.

## 5. Components

### Buttons
- **Shape:** Rounded rectangles, `rounded-lg` (`10px`). Small and icon-small buttons soften to `min(rounded-md, 12px)`.
- **Default size:** `h-8` (32px), `px-2.5`, `text-sm`, `font-medium`.
- **Variants:**
  - **default** (primary): `bg-primary` + `text-primary-foreground`. Used for the single decisive action on a surface (Upload, Generate, Save).
  - **outline:** `border-border` + `bg-background`. Used for inline actions next to a primary, or for secondary destructive paths.
  - **secondary:** `bg-secondary`. Used in dense toolbars where outline would over-line the surface.
  - **ghost:** No background, no border. Used for nav-back, dropdown triggers, table-row actions.
  - **destructive:** `bg-destructive/10` + `text-destructive`. Tinted, not saturated, so destructive actions read as available but not urgent.
  - **link:** Underlined indigo. Only for inline navigation in prose.
- **States:** `transition-all`, `active:translate-y-px` for a small tactile depress; focus-visible ring is the `--shadow-focus` token.

### Cards
- **Corner:** `rounded-xl` (14px).
- **Surface:** `bg-card` (#ffffff).
- **Padding:** `p-4` default, `p-5` for content-dense cards, `p-6` for review surfaces.
- **Shadow:** `shadow-card` at rest, `shadow-card-hover` on hover for interactive cards only.
- **Hover:** `transition-[transform,box-shadow] duration-[var(--duration-normal)] ease-[var(--ease-out)]`. Interactive cards lift `translateY(-1px)`; static cards don't move.
- **Nesting:** Forbidden. Use spacing and hairlines to group inside a card.

### Inputs
- **Shape:** `rounded-lg`, `h-9` (36px), `px-3 py-1.5`, `text-[0.9375rem]`.
- **Surface:** `bg-background` + `border-input` + `shadow-xs`.
- **Focus:** Border shifts to `ring` (Signal Indigo) and gains the `--shadow-focus` glow. No animation on the border itself; only the shadow grows.
- **Disabled:** `bg-input/50`, `opacity-50`, cursor-not-allowed.
- **Invalid:** Border becomes `destructive`, ring becomes destructive-tinted.

### Badges
- **Shape:** Full pill (`rounded-4xl`, 999px-equivalent at this scale), `h-5`, `px-2 py-0.5`, `text-xs font-medium`.
- **Variants** mirror buttons (default, secondary, destructive, outline, ghost). Used for recording status, document type, task priority.
- **Rule:** Always carry text. No icon-only badges.

### Tables
- Borderless rows, `text-sm`. Headers are `label` size in `muted-foreground`. Hover row gets `bg-muted/40`. No alternating row stripes; the eye uses spacing instead.

### Sidebar Navigation
- **Style:** Tinted sidebar surface (`--sidebar`), nav items as full-width text+icon rows, `rounded-md` highlight.
- **Active state:** `bg-sidebar-accent` with `text-sidebar-accent-foreground`. No bar, no stripe, no underline.
- **Collapsed state:** Icon-only with tooltip; rail visible.

### Page Shell
- **Header:** `h-12`, `border-b border-border/60`, fluid `paddingInline: clamp(1rem, 2.5vw, 2rem)`. No shadow.
- **Main:** Fluid horizontal padding, `paddingBlock: clamp(1.5rem, 3vw, 2.5rem)`. Inner content capped at `max-w-[1400px] mx-auto`.
- **Vertical rhythm:** Page sections use `space-y-8` (32px) by default. Header block uses `space-y-2` so heading + subtitle group tightly.

## 6. Do's and Don'ts

### Do
- **Do** use Signal Indigo only for primary action, current selection, focus, and live data. If you can replace it with `foreground`, do.
- **Do** cap prose surfaces at 72ch and center them. Wide monitors get margin, not stretched text.
- **Do** tint every neutral toward hue 265 (chroma 0.005-0.01). No flat grays.
- **Do** pair status colors with text and icons. Color alone is never the signal.
- **Do** use the `--shadow-card` + `--shadow-card-hover` pair as a single unit. Interactive cards lift 1px on hover; static cards stay put.
- **Do** vary spacing for rhythm. Tight inside groupings (8-16px), generous between sections (32-48px).
- **Do** keep page headers (h1 + subtitle) tightly stacked above the first content block.
- **Do** match Space Grotesk weights 600-700 to headings only; never use it for body.

### Don't
- **Don't** ship purple-mesh gradient heroes, animated blobs, or sparkle iconography. These read as generic AI SaaS, the exact aesthetic this product rejects.
- **Don't** use gradient text (`background-clip: text`). Headings stay solid `foreground`.
- **Don't** apply glassmorphism (`backdrop-blur`) as a default surface. It belongs to dialogs over media at most.
- **Don't** template hero-metric blocks (big number, small label, supporting stats, gradient accent). The dashboard's stat row shows real data and reads as the operations summary; never decorate fake numbers.
- **Don't** wrap everything in a card. Most things, page titles, subtitles, inline lists, do not need containment.
- **Don't** nest cards inside cards. Use spacing and a hairline.
- **Don't** use side-stripe borders (colored `border-left` accents on rows or callouts). Replace with a full border, a tinted background, or nothing.
- **Don't** decorate with shadow. Shadows mean elevation or focus, nothing else.
- **Don't** lean on Jira-style dense toolbars or boxy enterprise chrome. The product is calm and reduced; chrome recedes.
- **Don't** use em dashes in UI copy. Use commas, colons, semicolons, periods, or parentheses.
- **Don't** uppercase UI labels. Plain prose-case throughout.
- **Don't** animate layout properties (`width`, `height`, `top`, `left`). Animate `transform` and `opacity` only.
- **Don't** introduce a second accent color. Allure has one voice, and it's indigo.

