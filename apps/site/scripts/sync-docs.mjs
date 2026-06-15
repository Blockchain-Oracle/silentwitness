#!/usr/bin/env node
/**
 * Mirror canonical docs/*.md → apps/site/content/docs/*.mdx so Fumadocs
 * picks them up. Adds YAML frontmatter (title + description) extracted from
 * the first H1 + first blockquote/paragraph.
 *
 * Source of truth stays at `docs/*.md` (GitHub renders them unchanged).
 * The site is a renderer, not a content store — this script is idempotent
 * and runs as `pnpm predev` / `pnpm prebuild`.
 *
 * Hand-curated pages (index.mdx, quickstart.mdx, architecture.mdx) are
 * preserved — sync only writes files matching the canonical doc list.
 */

import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SITE_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(SITE_ROOT, "..", "..");
const SRC = path.join(REPO_ROOT, "docs");
const DST = path.join(SITE_ROOT, "content", "docs");

// Files we mirror from repo docs/*.md → content/docs/*.mdx. Kept explicit so
// internal sprint docs (CICD_SPEC, BRAINSTORM, stories/) never accidentally
// land on the public site.
const CANONICAL = {
  "SETUP_GUIDE.md": "setup-guide.mdx",
  "ACCURACY_REPORT.md": "accuracy-report.mdx",
  "THREE_CLAIM_TRACE.md": "three-claim-trace.mdx",
  "DATASETS.md": "datasets.mdx",
  "TRY_IT_OUT.md": "try-it-out.mdx",
  "architecture.md": "architecture-deep-dive.mdx",
};

function extractFrontmatter(markdown, sourceName) {
  const lines = markdown.split("\n");
  let title = sourceName.replace(/\.md$/, "");
  let description = null;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!title && line.startsWith("# ")) {
      title = line.slice(2).trim();
    } else if (line.startsWith("# ")) {
      title = line.slice(2).trim();
    } else if (
      description === null &&
      (line.startsWith("> ") || (line.trim().length > 20 && !line.startsWith("#")))
    ) {
      description = line.replace(/^>\s*/, "").trim().slice(0, 200);
      if (description) break;
    }
  }
  // Escape quotes for YAML safety.
  const safeTitle = title.replace(/"/g, "'");
  const safeDescription = description ? description.replace(/"/g, "'") : "";
  return safeDescription
    ? `---\ntitle: "${safeTitle}"\ndescription: "${safeDescription}"\n---\n\n`
    : `---\ntitle: "${safeTitle}"\n---\n\n`;
}

async function main() {
  if (!existsSync(DST)) await mkdir(DST, { recursive: true });

  let mirrored = 0;
  for (const [src, dst] of Object.entries(CANONICAL)) {
    const srcPath = path.join(SRC, src);
    if (!existsSync(srcPath)) {
      console.warn(`sync-docs: skipping missing ${src}`);
      continue;
    }
    const content = await readFile(srcPath, "utf-8");
    const fm = extractFrontmatter(content, src);
    // Strip the original H1 (it duplicates the frontmatter title in Fumadocs).
    const bodyLines = content.split("\n");
    const h1Index = bodyLines.findIndex((line) => line.startsWith("# "));
    let body =
      h1Index >= 0
        ? bodyLines.slice(h1Index + 1).join("\n").replace(/^\s+/, "")
        : content;

    // MDX-safety transforms — these are valid GitHub markdown but invalid MDX:
    //
    // 1. HTML comments `<!-- ... -->` → MDX comments `{/* ... */}`
    body = body.replace(/<!--([\s\S]*?)-->/g, (_, inner) => `{/*${inner}*/}`);
    //
    // 2. Autolinks `<https://...>` → bare URL (MDX parses `<https://` as JSX).
    //    Inside code fences we DO NOT want to touch URLs, but for the docs we
    //    mirror these only appear in prose, so a global replace is safe.
    body = body.replace(/<(https?:\/\/[^\s>]+)>/g, "$1");
    //
    // 3. Stand-alone `<` not followed by an identifier (e.g. `<10` in prose).
    //    Escape with HTML entity so MDX leaves it alone. The negative
    //    lookahead protects real JSX tags + opening code-fence `<` shells.
    body = body.replace(/<(?=[\s\d=])/g, "&lt;");

    await writeFile(path.join(DST, dst), fm + body, "utf-8");
    mirrored++;
  }

  // Sanity-check what hand-curated files survived.
  const present = await readdir(DST);
  console.log(
    `sync-docs: mirrored ${mirrored} canonical docs; ${present.length} files now in content/docs/`,
  );
}

main().catch((err) => {
  console.error("sync-docs failed:", err);
  process.exit(1);
});
