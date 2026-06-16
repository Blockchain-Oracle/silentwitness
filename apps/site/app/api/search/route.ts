import { createFromSource } from "fumadocs-core/search/server";

import { source } from "@/lib/source";

// Build-time index — Fumadocs uses it for client-side search in dev.
// Pagefind takes over at build time (`pnpm run build:pagefind` writes the
// static index to `public/pagefind/`), so this route is fallback.
export const { GET } = createFromSource(source);
