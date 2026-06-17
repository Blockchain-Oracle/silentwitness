#!/usr/bin/env node
/**
 * Unit tests for apps/site/scripts/sync-docs.mjs MDX-safety transforms.
 *
 * Tests focus on the silent-corruption risks flagged by PR #238 review:
 *
 *   - In-fence tracking: never touch URLs / `<` / `<!--` inside a ``` fence.
 *   - HTML comment greed: each `<!-- … -->` becomes its own MDX comment.
 *   - Autolink correctness: `<https://x>` becomes a bare URL outside fences.
 *   - `<` escape doesn't clobber JSX components.
 *   - extractFrontmatter copes with H1 containing commas/quotes/backticks.
 *
 * Run: `node --test apps/site/scripts/sync-docs.test.mjs`
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  applyMdxSafety,
  extractFrontmatter,
  rewriteSiteLinks,
  _escapeYamlString,
} from "./sync-docs.mjs";

// ---------------------------------------------------------------------------
// applyMdxSafety — fence tracking
// ---------------------------------------------------------------------------

test("autolink outside fence is stripped to bare URL", () => {
  const input = "Visit <https://example.com> for details.";
  const output = applyMdxSafety(input);
  assert.equal(output, "Visit https://example.com for details.");
});

test("autolink INSIDE backtick fence is preserved verbatim", () => {
  const input = [
    "Run this command:",
    "```bash",
    "curl <https://example.com/install.sh> | bash",
    "```",
    "More prose.",
  ].join("\n");
  const output = applyMdxSafety(input);
  assert.ok(
    output.includes("curl <https://example.com/install.sh> | bash"),
    `expected URL inside fence to be untouched, got:\n${output}`,
  );
});

test("HTML comment outside fence becomes MDX comment", () => {
  const input = "Before\n<!-- hidden -->\nAfter";
  const output = applyMdxSafety(input);
  assert.ok(output.includes("{/* hidden */}"));
  assert.ok(!output.includes("<!-- hidden -->"));
});

test("HTML comment INSIDE fence is preserved verbatim", () => {
  const input = "```html\n<!-- a literal HTML comment -->\n```";
  const output = applyMdxSafety(input);
  assert.ok(output.includes("<!-- a literal HTML comment -->"));
  assert.ok(!output.includes("{/*"));
});

test("multiple HTML comments on one line each become their own MDX comment", () => {
  const input = "<!--a--> mid <!--b-->";
  const output = applyMdxSafety(input);
  assert.equal(output, "{/*a*/} mid {/*b*/}");
});

test("`<` followed by digit outside fence is escaped to &lt;", () => {
  const input = "It runs in <10ms";
  const output = applyMdxSafety(input);
  assert.equal(output, "It runs in &lt;10ms");
});

test("`<` INSIDE fence is preserved verbatim", () => {
  const input = "```\nif x <10: print(x)\n```";
  const output = applyMdxSafety(input);
  assert.ok(output.includes("if x <10: print(x)"));
  assert.ok(!output.includes("&lt;"));
});

test("JSX component opener is NOT escaped even outside fence", () => {
  const input = "Use <Callout type=\"warn\">careful</Callout> in prose.";
  const output = applyMdxSafety(input);
  // Both `<Callout` and `</Callout>` survive untouched.
  assert.ok(output.includes("<Callout"));
  assert.ok(output.includes("</Callout>"));
});

test("tilde-fence is also tracked", () => {
  const input = "~~~\ncurl <https://x>\n~~~\nthen <https://y>";
  const output = applyMdxSafety(input);
  // Inside the ~~~ fence: untouched.
  assert.ok(output.includes("curl <https://x>"));
  // After fence: stripped.
  assert.ok(output.includes("then https://y"));
});

// ---------------------------------------------------------------------------
// rewriteSiteLinks — site routes vs repo-only artifacts
// ---------------------------------------------------------------------------

test("rewriteSiteLinks maps canonical docs to site routes", () => {
  const input =
    "See [Accuracy](ACCURACY_REPORT.md) and [Starter cases](./STARTER_CASES.md#nitroba).";
  const output = rewriteSiteLinks(input);
  assert.equal(
    output,
    "See [Accuracy](/docs/accuracy-report) and [Starter cases](/docs/starter-cases#nitroba).",
  );
});

test("rewriteSiteLinks maps repo-only logs to GitHub", () => {
  const input = "Open [critic](execution_logs/gpt55_100pct_run/critic.jsonl).";
  const output = rewriteSiteLinks(input);
  assert.equal(
    output,
    "Open [critic](https://github.com/Blockchain-Oracle/silentwitness/blob/main/docs/execution_logs/gpt55_100pct_run/critic.jsonl).",
  );
});

test("rewriteSiteLinks maps diagram assets to the local site public path", () => {
  const input = "See ![Architecture](../assets/brand/diagram-A-architecture.png).";
  const output = rewriteSiteLinks(input);
  assert.equal(output, "See ![Architecture](/brand/diagram-A-architecture.png).");
});

test("rewriteSiteLinks leaves fenced links untouched", () => {
  const input = "```md\n[Accuracy](ACCURACY_REPORT.md)\n```\n[Accuracy](ACCURACY_REPORT.md)";
  const output = rewriteSiteLinks(input);
  assert.ok(output.includes("```md\n[Accuracy](ACCURACY_REPORT.md)\n```"));
  assert.ok(output.includes("[Accuracy](/docs/accuracy-report)"));
});

// ---------------------------------------------------------------------------
// extractFrontmatter — pathological titles
// ---------------------------------------------------------------------------

test("extractFrontmatter handles quotes in H1", () => {
  const input = '# Tool, v3 "release"\n\nSome description.';
  const fm = extractFrontmatter(input, "x.md");
  // Title must be valid YAML double-quoted — quotes escaped as \"
  assert.ok(fm.includes('title: "Tool, v3 \\"release\\""'));
});

test("extractFrontmatter handles backslash in H1", () => {
  const input = "# Path\\to\\thing\n\nA description.";
  const fm = extractFrontmatter(input, "x.md");
  // Double-quoted YAML requires backslash escaping.
  assert.ok(fm.includes('title: "Path\\\\to\\\\thing"'));
});

test("extractFrontmatter picks blockquote as description", () => {
  const input = "# Title\n\n> This is the blockquote description that should appear.\n\nMore.";
  const fm = extractFrontmatter(input, "x.md");
  assert.ok(fm.includes('description: "This is the blockquote description'));
});

test("extractFrontmatter newline inside description is flattened to space", () => {
  const longLine = "Long descriptive paragraph that wraps around the page width and contains useful info.";
  const input = `# Title\n\n${longLine}\n\nMore.`;
  const fm = extractFrontmatter(input, "x.md");
  // Whatever description it picks, no raw newline can sit in the YAML
  // double-quoted string — YAML would terminate the value on \n.
  const descMatch = fm.match(/description: "([^"]*)"/);
  if (descMatch) {
    assert.ok(!descMatch[1].includes("\n"), `description must be single-line, got ${JSON.stringify(descMatch[1])}`);
  }
});

test("extractFrontmatter title fallback uses filename when no H1", () => {
  const input = "No heading here.\n\nJust prose.";
  const fm = extractFrontmatter(input, "MYFILE.md");
  assert.ok(fm.includes('title: "MYFILE"'));
});

// ---------------------------------------------------------------------------
// _escapeYamlString
// ---------------------------------------------------------------------------

test("_escapeYamlString escapes double quotes and backslashes", () => {
  assert.equal(_escapeYamlString('a"b\\c'), 'a\\"b\\\\c');
});

test("_escapeYamlString flattens newlines to spaces", () => {
  assert.equal(_escapeYamlString("a\nb\r\nc"), "a b c");
});
