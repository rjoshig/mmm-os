# CLAUDE.md — mmm-os front-end

Design considerations and conventions for the Next.js UI. **All new UI MUST match
this design language.** When you add screens or components, reuse these tokens and
patterns rather than introducing new colors, fonts, or spacing.

## Design source of truth

The visual language is **replicated from the reference UI**:

- Repo: `rjoshig/compare-file`, branch `dev`, path `ui2`
  (https://github.com/rjoshig/compare-file/tree/dev/ui2).

The values below were extracted from that reference and are the authoritative
tokens for this project. If the reference changes, reconcile here deliberately —
do not drift ad hoc.

## Stack

- **Next.js 15** (App Router) · **React 18** · **TypeScript (strict)**.
- **Tailwind CSS 3.4** + PostCSS + autoprefixer.
- **next-themes** for class-based light/dark switching.
- **lucide-react** for icons.
- **clsx** + **tailwind-merge** via the `cn()` helper (`lib/utils.ts`).
- Path alias **`@/*`** → project root.
- Prisma for the UI database (see below).

## Color palette (the actual extracted tokens)

Colors are **shadcn-style HSL CSS variables** defined in `app/globals.css` and
consumed through Tailwind as `hsl(var(--token))` (mapped in `tailwind.config.ts`).
Values are `H S% L%` triples. This is the base **"default" palette** (blue primary).

| Token                                | Light (`:root`)               | Dark (`.dark`)                |
| ------------------------------------ | ----------------------------- | ----------------------------- |
| `--background`                       | `210 40% 98%`                 | `222 47% 7%`                  |
| `--foreground`                       | `222 47% 11%`                 | `210 40% 96%`                 |
| `--card` / `--card-foreground`       | `0 0% 100%` / `222 47% 11%`   | `222 44% 10%` / `210 40% 96%` |
| `--primary` / `--primary-foreground` | `221 83% 53%` / `210 40% 98%` | `217 91% 60%` / `222 47% 11%` |
| `--secondary` / `-foreground`        | `210 40% 96%` / `222 47% 11%` | `217 33% 17%` / `210 40% 96%` |
| `--muted` / `--muted-foreground`     | `210 40% 96%` / `215 16% 47%` | `217 33% 15%` / `215 20% 65%` |
| `--accent` / `--accent-foreground`   | `210 40% 94%` / `222 47% 11%` | `217 33% 20%` / `210 40% 96%` |
| `--destructive` / `-foreground`      | `0 72% 51%` / `210 40% 98%`   | `0 63% 50%` / `210 40% 98%`   |
| `--success` / `--success-foreground` | `142 71% 45%` / `210 40% 98%` | `142 69% 48%` / `222 47% 11%` |
| `--border` / `--input`               | `214 32% 91%`                 | `217 33% 20%` / `217 33% 22%` |
| `--ring`                             | `221 83% 53%`                 | `217 91% 60%`                 |
| `--tertiary` / `-foreground`         | `48 96% 53%` / `222 47% 11%`  | `48 96% 53%` / `222 47% 11%`  |
| `--radius`                           | `0.5rem`                      | `0.5rem`                      |

### Alternate palettes (available, not active by default)

The reference ships additional config-driven palettes. They are documented here
as available options if we later want a theme switcher (the base default is
active now):

- **light-blue-yellow** — primary `199 89% 48%` (sky blue), secondary/tertiary `48 96% 53%` (yellow).
- **classic-teal** — primary `200 100% 20%` (#004364), secondary `191 100% 40%` (#00A6CA), tertiary `51 100% 49%` (#FCD800).

## Typography

- **Font:** `Inter` via `next/font/google` (`display: "swap"`), applied as the
  `className` on `<html>` in `app/layout.tsx`.
- **Density:** `html { font-size: 14px }` is the global density lever; `body`
  sits at `0.9375rem` (~13.1px). Antialiased, `text-rendering: optimizeLegibility`,
  `font-feature-settings: "cv11", "ss01"`.
- **Monospace:** `.mono` = `ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, monospace`.

## Spacing, layout & breakpoints

- **Border radius:** `lg = var(--radius)` (0.5rem); `md`/`sm` derived (`-2px`/`-4px`).
- **App shell:** a `flex` row with the sidebar (added in Phase 6) and
  `<main class="h-screen flex-1 overflow-y-auto">`; content is centered in
  `mx-auto max-w-7xl px-6 py-5`.
- **Spacing scale:** standard Tailwind. Common values in the reference: card
  padding `p-4`/`p-5`, grid `gap-4`, section rhythm `space-y-6` / `mt-4`,
  page padding `px-6 py-5`.
- **Breakpoints:** standard Tailwind (`sm` 640, `md` 768, `lg` 1024, `xl` 1280,
  `2xl` 1536). The reference uses `sm:` and `lg:` most; the content container caps
  at `max-w-7xl` (80rem).

## Component & styling conventions

- **Functional components + hooks only.** No business logic in components; data
  access goes through a thin client/API layer (added with feature work).
- Merge classes with `cn()` (`lib/utils.ts`); never hand-concatenate Tailwind strings.
- Use semantic tokens (`text-muted-foreground`, `bg-card`, `text-primary`,
  `text-success`, `text-destructive`) — **do not** hardcode hex colors.
- Icons come from `lucide-react`, sized `h-4 w-4` inline with text.
- Numbers in tables use `tabular-nums`.
- Mark interactive/client pages with `"use client"`.

## UI database (Prisma)

- The UI has its **own** database (`front-end/prisma/schema.prisma`), separate
  from the backend database. SQLite in dev (`DATABASE_URL="file:./dev.db"`),
  swappable to Postgres by changing the datasource `provider` + `DATABASE_URL`
  and regenerating/migrating. Keep the schema portable — avoid Postgres-only
  native types until the swap. See `../docs/architecture.md`.

## Scope note — Phase 6

Feature screens are **not** built yet. **Phase 6** implements the Review UI —
job dashboard, mapping review, action-based transformation builder, and
validation review — all **preview-driven** (live before/after on sample rows).
**No raw JSON is ever exposed to users**; UI actions author config behind the
scenes. See `../docs/phases/phase-06-review-ui-nextjs.md`.
