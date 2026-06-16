# @silentwitness/site

> Premium Fumadocs + Pagefind documentation site for SilentWitness, deployed on Vercel.

Mirrors the [story-cdr/cdrkit.xyz](https://github.com/Blockchain-Oracle/story-cdr) stack: Next.js 16 + React 19 + fumadocs-core/fumadocs-mdx/fumadocs-ui + Pagefind static-search index. No CMS, no SaaS search dependency, no Algolia API key.

## Local dev

```bash
pnpm install                # repo root
pnpm --filter @silentwitness/site dev
# open http://localhost:3000
```

`pnpm dev` runs `sync-docs` first (mirrors `docs/*.md` → `content/docs/*.mdx` with frontmatter prepended), then `next dev`.

## Build

```bash
pnpm --filter @silentwitness/site build
# next build + pagefind static index → public/pagefind/
```

## Deploy

Pushes to `main` trigger Vercel automatically — see `vercel.json` at the repo root. Preview deployments fire on every PR. Live URL: https://silentwitness.vercel.app.

## Content sources

| Path | Source | Purpose |
|---|---|---|
| `content/docs/index.mdx` | hand-curated | Landing page (canonical) |
| `content/docs/quickstart.mdx` | hand-curated | Five-minute install + investigate |
| `content/docs/architecture.mdx` | hand-curated | High-level boundaries + architecture visuals |
| `content/docs/*.mdx` (rest) | mirrored from `docs/*.md` via `scripts/sync-docs.mjs` | The canonical docs/ tree is the source of truth; this site is a renderer. |

Only judge-facing docs are mirrored — see the `CANONICAL` allow-list in `scripts/sync-docs.mjs`.

## Brand tokens

Indigo + forest-green + warm-beige palette in `app/globals.css`. Designed to mirror the designer's `cdr-kit` palette vendored under repo `design/` (when those assets land).
