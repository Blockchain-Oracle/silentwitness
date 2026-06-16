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
 * preserved — sync only writes files in the canonical allow-list.
 */

import { readFile, writeFile, mkdir, readdir, copyFile, unlink } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SITE_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(SITE_ROOT, "..", "..");
const SRC = path.join(REPO_ROOT, "docs");
const DST = path.join(SITE_ROOT, "content", "docs");
const DIAGRAMS_SRC = path.join(SRC, "diagrams");
const DIAGRAMS_DST = path.join(SITE_ROOT, "public", "diagrams");

// Files we mirror from repo docs/*.md → content/docs/*.mdx. Kept explicit so
// internal sprint docs (CICD_SPEC, BRAINSTORM, stories/) never accidentally
// land on the public site. Missing source → fatal (see main()) so a bad
// rebase doesn't ship empty docs to Vercel.
const CANONICAL = {
  "SETUP_GUIDE.md": "setup-guide.mdx",
  "ACCURACY_REPORT.md": "accuracy-report.mdx",
  "THREE_CLAIM_TRACE.md": "three-claim-trace.mdx",
  "DATASETS.md": "datasets.mdx",
  "TRY_IT_OUT.md": "try-it-out.mdx",
};

const DOC_ROUTES = new Map([
  ["SETUP_GUIDE.md", "/docs/setup-guide"],
  ["ACCURACY_REPORT.md", "/docs/accuracy-report"],
  ["THREE_CLAIM_TRACE.md", "/docs/three-claim-trace"],
  ["DATASETS.md", "/docs/datasets"],
  ["TRY_IT_OUT.md", "/docs/try-it-out"],
]);

const GITHUB_DOCS_ROOT = "https://github.com/Blockchain-Oracle/silentwitness";

// JSX components we expect to find in real MDX prose (after migration).
// Any `<Name>` token starting with a capital letter is treated as JSX and
// left alone — the regex never escapes these. Lowercase tags like `<https>`
// are NOT JSX and ARE escaped/de-fanged.
const JSX_COMPONENT_RE = /^<[A-Z][A-Za-z0-9]*[\s/>]/;

function _escapeYamlString(value) {
  // YAML double-quoted strings need backslash + quote escaping. We use
  // double-quoted strings (not single) because they support \n etc., and we
  // want any embedded newline in a description to be \n-escaped, not
  // wrap to a new YAML line and break parsing.
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r?\n/g, " ");
}

function extractFrontmatter(markdown, sourceName) {
  const lines = markdown.split("\n");
  let title = sourceName.replace(/\.md$/, "");
  let description = null;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("# ")) {
      title = line.slice(2).trim();
      continue;
    }
    if (
      description === null &&
      (line.startsWith("> ") || (line.trim().length > 20 && !line.startsWith("#")))
    ) {
      description = line.replace(/^>\s*/, "").trim().slice(0, 200);
      if (description) break;
    }
  }
  const safeTitle = _escapeYamlString(title);
  const safeDescription = description ? _escapeYamlString(description) : "";
  return safeDescription
    ? `---\ntitle: "${safeTitle}"\ndescription: "${safeDescription}"\n---\n\n`
    : `---\ntitle: "${safeTitle}"\n---\n\n`;
}

/**
 * Apply MDX-safety transforms ONLY to prose, never inside fenced code
 * blocks. Walks the markdown line-by-line, tracking whether the cursor is
 * inside a ```fence```. Inside a fence we yield the line unchanged — code
 * samples like `curl <https://...>` or `<10ms` MUST render literally.
 *
 * Outside a fence we apply three transforms:
 *
 *   1. `<!-- HTML comment -->` → `{/* MDX comment * /}` — MDX rejects the
 *      HTML form.
 *   2. `<https://...>` autolink → bare URL — MDX parses `<https://` as a
 *      JSX opening tag and chokes.
 *   3. `<` followed by whitespace / digit / equals → `&lt;` — MDX would
 *      otherwise try to parse it as a JSX tag opener. JSX components
 *      (`<Name…`) start with a capital letter and are LEFT alone by the
 *      explicit JSX_COMPONENT_RE guard.
 */
function applyMdxSafety(body) {
  const lines = body.split("\n");
  const fenceRe = /^(```|~~~)/;
  let inFence = false;
  const out = [];
  for (const line of lines) {
    if (fenceRe.test(line)) {
      inFence = !inFence;
      out.push(line);
      continue;
    }
    if (inFence) {
      out.push(line);
      continue;
    }
    let transformed = line.replace(/<!--([\s\S]*?)-->/g, (_, inner) => `{/*${inner}*/}`);
    transformed = transformed.replace(/<(https?:\/\/[^\s>]+)>/g, "$1");
    // Escape `<` followed by whitespace/digit/equals, BUT only if what
    // follows doesn't look like a JSX component opener. The substring
    // check guards against `<Name`, `<Cards>`, etc. — those stay literal
    // so the docs can ship custom Fumadocs components without losing
    // them to over-eager escaping.
    transformed = transformed.replace(/</g, (match, offset, str) => {
      const tail = str.slice(offset);
      if (JSX_COMPONENT_RE.test(tail)) return match;
      const next = str.charAt(offset + 1);
      if (next === "" || /[\s\d=]/.test(next)) return "&lt;";
      return match;
    });
    out.push(transformed);
  }
  return out.join("\n");
}

function _githubPath(kind, relPath) {
  return `${GITHUB_DOCS_ROOT}/${kind}/main/${relPath}`;
}

function _rewriteHref(href) {
  if (
    href.startsWith("http://") ||
    href.startsWith("https://") ||
    href.startsWith("mailto:") ||
    href.startsWith("#") ||
    href.startsWith("/")
  ) {
    return href;
  }

  const [pathPart, anchor = ""] = href.split("#", 2);
  const anchorSuffix = anchor ? `#${anchor}` : "";
  const normalized = pathPart.replace(/^\.?\//, "").replace(/^docs\//, "");
  const route = DOC_ROUTES.get(normalized);
  if (route) return `${route}${anchorSuffix}`;

  if (normalized === "../LICENSE" || normalized === "LICENSE") {
    return _githubPath("blob", "LICENSE");
  }
  if (normalized === "../NOTICES.md" || normalized === "NOTICES.md") {
    return _githubPath("blob", "NOTICES.md");
  }

  if (normalized.startsWith("diagrams/")) {
    return `/${normalized}`;
  }

  if (
    normalized.startsWith("execution_logs/") ||
    normalized.startsWith("EXAMPLE_EXECUTION_LOGS/")
  ) {
    const kind = /\.[A-Za-z0-9]+$/.test(normalized) ? "blob" : "tree";
    return _githubPath(kind, `docs/${normalized}`);
  }

  return href;
}

function rewriteSiteLinks(body) {
  const lines = body.split("\n");
  const fenceRe = /^(```|~~~)/;
  let inFence = false;
  const out = [];
  for (const line of lines) {
    if (fenceRe.test(line)) {
      inFence = !inFence;
      out.push(line);
      continue;
    }
    if (inFence) {
      out.push(line);
      continue;
    }
    out.push(line.replace(/\]\(([^)]+)\)/g, (_, href) => `](${_rewriteHref(href)})`));
  }
  return out.join("\n");
}

async function main() {
  if (!existsSync(DST)) await mkdir(DST, { recursive: true });
  if (!existsSync(DIAGRAMS_DST)) await mkdir(DIAGRAMS_DST, { recursive: true });

  if (existsSync(DIAGRAMS_SRC)) {
    for (const entry of await readdir(DIAGRAMS_DST)) {
      await unlink(path.join(DIAGRAMS_DST, entry));
    }
    for (const entry of await readdir(DIAGRAMS_SRC)) {
      const srcPath = path.join(DIAGRAMS_SRC, entry);
      const dstPath = path.join(DIAGRAMS_DST, entry);
      await copyFile(srcPath, dstPath);
    }
  }

  const missing = [];
  let mirrored = 0;
  for (const [src, dst] of Object.entries(CANONICAL)) {
    const srcPath = path.join(SRC, src);
    if (!existsSync(srcPath)) {
      missing.push(src);
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
    body = rewriteSiteLinks(applyMdxSafety(body));
    await writeFile(path.join(DST, dst), fm + body, "utf-8");
    mirrored++;
  }

  if (missing.length > 0) {
    // Fail loudly — the canonical list is intentionally curated; absence
    // means a bad rebase or a typo, not a feature. Override with
    // SYNC_DOCS_ALLOW_MISSING=1 for local dev iteration where you've
    // staged but not yet committed a renamed doc.
    const msg = `sync-docs: ${missing.length} canonical doc(s) missing: ${missing.join(", ")}`;
    if (process.env.SYNC_DOCS_ALLOW_MISSING === "1") {
      console.warn(`${msg} (SYNC_DOCS_ALLOW_MISSING=1 set — continuing)`);
    } else {
      console.error(msg);
      console.error("set SYNC_DOCS_ALLOW_MISSING=1 to continue with partial mirror");
      process.exit(1);
    }
  }

  const present = await readdir(DST);
  console.log(
    `sync-docs: mirrored ${mirrored} canonical docs; ${present.length} files now in content/docs/`,
  );
}

// Exported for testing — see tests/unit/site/test_sync_docs.test.mjs.
export { applyMdxSafety, extractFrontmatter, rewriteSiteLinks, _escapeYamlString };

// Run when invoked directly (not when imported by a test).
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error("sync-docs failed:", err);
    process.exit(1);
  });
}
