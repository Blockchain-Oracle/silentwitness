# Story — README polish (PRD §11 shape + inline Mermaid + above-the-fold demo asset)

**ID:** story-readme-polish
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-scaffold-uv-pyproject (LICENSE + skeleton repo), story-docker-baseline (Docker Compose path), story-cli-install-claude-code (3-command native path), story-architecture-diagram-png (Mermaid source for the inline block), story-cli-investigate (the screenshot/GIF target)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** judge opening the SilentWitness Devpost gallery entry on first contact
**I want to** see — in the README's first screen — the project name + one-line pitch, the ≤3-minute demo video, an above-the-fold screenshot of the report-with-verify-links, the verbatim 3-command native install path AND the 2-command Docker Compose path, an inline Mermaid architecture diagram with the six architectural boundaries labeled separately from the two prompt-based ones, and the MIT license badge
**So that** Devpost Rules §4 deliverables 1, 2, 3, 7 are visibly satisfied without scrolling and the "Usability and Documentation" judging criterion (PRD §8 row 6) scores against a README that resembles the one the rubric describes (PRD §11 README shape verbatim; FR1 stock-SIFT 2026 install; FR10 Docker Compose).

---

## File modification map

- `README.md` — UPDATE (replaces the skeleton placed by story-scaffold-uv-pyproject) — the final judge-facing README. LOC budget: **≤400 lines total**. Section order matches PRD §11 verbatim:
  1. H1 title `# SilentWitness` immediately followed by one-line pitch blockquote (PRD §1 verbatim: *"SilentWitness — a hypothesis-first DFIR investigator whose report writes itself, with every claim locked to the tool that produced it."*).
  2. Badge row: MIT license, Python 3.12, CI status, model-agnostic indicator. Single line, ≤5 badges.
  3. **Demo video** — markdown link to the YouTube unlisted URL produced by story-devpost-submission. Until that story merges, the link is a placeholder anchor `<!-- DEMO_VIDEO_URL -->` plus a stub `https://youtu.be/PLACEHOLDER` so the line renders without breaking the gallery preview; story-devpost-submission swaps the placeholder for the real URL as its last commit.
  4. **Above-the-fold visual** — single PNG/GIF (`docs/assets/report-verify-links.png`, captured from a real `silentwitness investigate` run on the Nitroba case during the demo-recording session; ≤500 KB; alt text: "Markdown report with inline `[verify:audit_id]` links resolving to JSONL audit entries"). The asset itself is committed as part of story-devpost-submission; this story declares the markdown `![](...)` line and the alt text.
  5. **Quick start** — TWO numbered paths, verbatim shell, copy-paste-ready:
     - **(a) SIFT 2026 native — 3 commands** per PRD §11 + ux-spec §2.2:
       ```bash
       curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/<org>/silentwitness/main/install.sh | bash
       silentwitness init mr-evil-001 --examiner $USER
       silentwitness register-evidence mr-evil-001 /evidence/hacking-case
       silentwitness investigate mr-evil-001
       ```
       (Counts as 3 user-typed commands once `register-evidence` is chained off `init`; the README presents them as 3 numbered steps with the register-evidence call collapsed into step 2.)
     - **(b) Docker Compose — 2 commands** per PRD §11 + story-docker-baseline:
       ```bash
       docker compose up -d
       docker compose exec silentwitness silentwitness investigate mr-evil-001
       ```
  6. **Architecture** — inline Mermaid block (the same source-of-truth Mermaid that lives at `docs/diagrams/architecture.mmd` from story-architecture-diagram-png; this README EMBEDS the `.mmd` content via a build-time include script OR copy-pastes the canonical block — the story's coding agent uses the copy-paste path and adds a CI check that the two stay in sync). Six **architectural** boundaries explicitly labeled with the trailing tag `(architectural)`; two **prompt-based** boundaries labeled `(prompt-based — supplementary, not load-bearing)` per PRD §2 0:30–1:00 + Devpost rules requirement to distinguish prompt-vs-architectural guardrails.
  7. **What's novel** — paragraph from `research/protocol-sift-2026/refs/quotes-for-pitch.md` §G.2 (copied verbatim, with the placeholder project name replaced).
  8. **Try it out** — pointer to `docs/TRY_IT_OUT.md` for the long-form per-dataset walkthrough.
  9. **Accuracy report** — pointer to `docs/ACCURACY_REPORT.md` for measured Δ vs vanilla Protocol SIFT.
  10. **Datasets** — pointer to `docs/DATASETS.md`.
  11. **Example execution logs** — pointer to `docs/EXAMPLE_EXECUTION_LOGS/`.
  12. **Architecture deep-dive** — pointer to `docs/architecture.md`.
  13. **License** — MIT, single-line callout linking to `LICENSE`.
  14. **Acknowledgments** — paragraph crediting AppliedIR / Valhuntir (the SANS-cited bar) and teamdfir/protocol-sift (the baseline) per PRD §11 verbatim.
- `scripts/check_readme_gate.py` — NEW — ≤80 LOC pure-Python gate the CI calls (CICD_SPEC §4.1 adds it; this story registers the script + the test that proves it works). Reads `README.md`, asserts: (1) H1 is `# SilentWitness`; (2) first 100 lines contain a `youtu.be/` or `youtube.com/watch` link OR a documented placeholder marker `<!-- DEMO_VIDEO_URL -->`; (3) first 100 lines contain `![` alt-text image embed; (4) lines contain `curl ...install.sh | bash`; (5) lines contain `docker compose up`; (6) a ```` ```mermaid ```` fence is present; (7) the mermaid block contains the strings `(architectural)` AND `(prompt-based`; (8) the file contains a literal `MIT` license reference; (9) total line count ≤400; (10) zero occurrences of the banned vocabulary list from PRD §14 (`court-admissible`, `autonomous SOC`, `Ralph Wiggum`, `replaces L1`, `eliminates hallucinations`, `find evil` as marketing — the literal phrase `Find Evil!` is allowed when referring to the hackathon by name; the gate carves that out). Exit 0 on pass; exit 1 with the failing rule name on fail.
- `tests/unit/test_readme_gate.py` — NEW — ≥10 BDD scenarios via subprocess invocation of `scripts/check_readme_gate.py` against synthetic README fixtures in `tests/fixtures/readme/` (good / missing-mermaid / no-license / banned-vocab / too-long / etc.). Each scenario asserts the expected exit code + the expected stderr substring naming the failed rule.
- `tests/fixtures/readme/*.md` — NEW — ≥8 synthetic fixtures (one happy-path, one per failure rule, plus a corner-case where the banned phrase appears inside a code block and MUST still trigger — banned vocab is not carved out by code-block context).
- `docs/assets/.gitkeep` — NEW — placeholder so the directory exists; the real PNG/GIF lands via story-devpost-submission's demo-recording pass.

The coding agent must NOT touch `src/silentwitness_mcp/` or `src/silentwitness_agent/` from this story.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given README.md exists in the repo root
When  `wc -l README.md` runs
Then  the line count is ≤400

Given README.md exists
When  the first 100 lines are read
Then  they contain the H1 `# SilentWitness` on or before line 5
And   they contain the one-line pitch verbatim from PRD §1
And   they contain a YouTube link OR the `<!-- DEMO_VIDEO_URL -->` placeholder
And   they contain an `![` image embed
And   they contain `curl` + `install.sh` + `| bash` on a single shell-fenced line
And   they contain `docker compose up` on a shell-fenced line

Given README.md contains the architecture section
When  the `mermaid` code block is extracted
Then  it contains ≥6 strings matching `\(architectural\)`
And   it contains ≥2 strings matching `\(prompt-based`
And   it parses as valid Mermaid (verified by `mmdc -i -` returning exit 0)

Given README.md is scanned for banned vocabulary
When  `grep -iE "court-admissible|autonomous soc|ralph wiggum|replaces l1|eliminates hallucinations" README.md` runs
Then  exit code is 1 (no matches)

Given README.md is scanned for the LICENSE link
When  `grep -E "\[MIT\]\(.*LICENSE\)|LICENSE" README.md` runs
Then  exit code is 0

Given `scripts/check_readme_gate.py` exists
When  `uv run python scripts/check_readme_gate.py README.md` runs
Then  exit code is 0

Given `tests/unit/test_readme_gate.py` exists
When  `uv run pytest tests/unit/test_readme_gate.py -v` runs
Then  exit code is 0
And   ≥10 tests pass

Given a malformed README fixture missing the mermaid block
When  `uv run python scripts/check_readme_gate.py tests/fixtures/readme/no-mermaid.md` runs
Then  exit code is 1
And   stderr contains "rule: mermaid_block_present"

Given a malformed README fixture containing "court-admissible"
When  `uv run python scripts/check_readme_gate.py tests/fixtures/readme/banned-vocab.md` runs
Then  exit code is 1
And   stderr contains "rule: banned_vocab"

Given the inline mermaid block in README.md
When  it is compared byte-for-byte against the trimmed contents of `docs/diagrams/architecture.mmd`
Then  the two are identical (sync check — `scripts/check_readme_gate.py` enforces; `diff <(extract README mermaid) docs/diagrams/architecture.mmd` exits 0)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# README size cap
[ "$(wc -l < README.md)" -le 400 ] || { echo "README over 400 LOC"; exit 1; }

# README gate passes
uv run python scripts/check_readme_gate.py README.md

# Banned vocab clean
! grep -iE "court-admissible|autonomous soc|ralph wiggum|replaces l1|eliminates hallucinations" README.md

# Tests pass
uv run pytest tests/unit/test_readme_gate.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

# Mermaid block parses (requires story-architecture-diagram-png's mmdc install)
awk '/```mermaid/,/```/' README.md | sed '1d;$d' > /tmp/readme.mmd
mmdc -i /tmp/readme.mmd -o /tmp/readme.png -t dark -b transparent

# Mermaid block matches the canonical source-of-truth
diff <(awk '/```mermaid/,/```/' README.md | sed '1d;$d') docs/diagrams/architecture.mmd

# §14 banned-vocab check across the README
git diff main...HEAD -- README.md | grep -E "^\+" | grep -iE "(court-admissible|autonomous soc|ralph wiggum|replaces l1|eliminates hallucinations)"
# Must output nothing
```

---

## Notes for coding agent

- Source of truth: PRD §11 (README shape — five top-level items in order: title+pitch, demo asset, run-locally steps, architecture diagram, license; everything else is below-the-fold supplementary), PRD §10 (the 8 deliverables; README is the index linking to 1, 2, 3, 5, 6, 7, 8), PRD §1 (the one-line pitch — copy verbatim; do NOT paraphrase), PRD §14 (vocabulary discipline — banned list), architecture.md §2 (the canonical Mermaid block + the trust-boundary annotations), CICD_SPEC §1.2 (Usability and Documentation is one of six equally-weighted criteria — the README is the first contact), `research/protocol-sift-2026/refs/quotes-for-pitch.md` §G.2 (the "what's novel" paragraph — copy-paste with project name swap).
- The README skeleton arrives from story-scaffold-uv-pyproject as a near-empty file. This story **replaces** that skeleton with the final shape. Coding agent: read the current `README.md`, then overwrite — do NOT append.
- The Mermaid block in the README is a **byte-for-byte copy** of `docs/diagrams/architecture.mmd` (the source-of-truth maintained by story-architecture-diagram-png). The CI gate `scripts/check_readme_gate.py` enforces the byte-for-byte match via `diff`. When `architecture.mmd` changes, the README block MUST be regenerated. If a contributor edits the README's Mermaid block in isolation, the gate fails; they must edit `architecture.mmd` instead and re-copy. This avoids drift.
- The six architectural boundaries (per PRD §2 0:30–1:00) that MUST appear as labels in the Mermaid block:
  1. Typed MCP tool surface (architectural — destructive commands literally do not exist)
  2. bwrap kernel sandbox (architectural — kernel namespaces, not prompt)
  3. ro,noexec,nosuid evidence mount (architectural — kernel mount option, not prompt)
  4. Server-side citation gate (architectural — gate runs in MCP server, not in the model)
  5. Server-side entity gate (architectural — same)
  6. HMAC-SHA256 PBKDF2-600K-iter approval ledger (architectural — cryptographic, not prompt)
- The two prompt-based boundaries that MUST also appear, labeled separately:
  1. System-prompt senior-analyst frame (prompt-based — supplementary, not load-bearing)
  2. Tool-call advisories injected into reasoning (prompt-based — supplementary, not load-bearing)
- The label format is part of the gate. Use exactly `(architectural)` and `(prompt-based — supplementary, not load-bearing)`. The em-dash is U+2014.
- Demo video URL handling. Until story-devpost-submission lands, use `<!-- DEMO_VIDEO_URL -->` immediately before a stub `https://youtu.be/PLACEHOLDER` link. The README gate has a carve-out: it passes if EITHER a real YouTube URL appears OR the placeholder marker appears within the first 100 lines. story-devpost-submission's last action is `sed -i 's|https://youtu.be/PLACEHOLDER|<real-url>|' README.md` plus removing the placeholder comment.
- Above-the-fold image. The asset path is `docs/assets/report-verify-links.png`. The README references it via `![Markdown report with inline verify-link resolution](docs/assets/report-verify-links.png)`. The file itself is created during the demo-recording session as part of story-devpost-submission. This story commits a `docs/assets/.gitkeep` so the directory exists; the README reference is dead-link-safe because the README gate does NOT check that the image file exists (only that the markdown embed line is present) — this is intentional: the README ships first, the asset ships with the demo.
- Banned-vocab gate carve-outs (per PRD §14):
  - "Find Evil!" (with the trailing exclamation, used as the hackathon's proper name in the Acknowledgments section) is allowed. The gate's regex is `find evil(?![!])` so the trailing `!` form passes.
  - "court-admissible" — never allowed. Use "defensible audit trail" or "survives cross-examination."
  - "Ralph Wiggum" — never allowed in any committed file (community jargon; describe behavior instead).
  - "autonomous SOC" / "replaces L1" / "eliminates hallucinations" — never allowed (vendor-marketing phrases Rob T. Lee penalizes).
- The badge row uses shields.io badge URLs only; no proprietary services. The CI-status badge points to the GitHub Actions workflow `ci.yml` (per CICD_SPEC §4.1). Until the repo is public, the badge will 404; that's acceptable — the gate doesn't check badge resolution.
- LOC budget rationale: ≤400 lines forces a tight first-screen and pushes verbose content into the `docs/*.md` siblings (TRY_IT_OUT, DATASETS, ACCURACY_REPORT, EXAMPLE_EXECUTION_LOGS, architecture). PRD §11 explicitly designates these as below-the-fold supplementary; the README is the index, not the encyclopedia.
- Known pitfalls:
  1. Markdown linters (`markdownlint`, `mdformat`) will reflow trailing whitespace inside the Mermaid fenced block and silently break the byte-for-byte sync. Add a `<!-- markdownlint-disable MD013 -->` around the Mermaid block. The README gate does NOT run `mdformat`/`mdl` — it runs the custom Python gate only.
  2. The `youtu.be/` regex in the README gate must allow query strings (`?si=...`). Use `re.search(r"(youtu\.be/[A-Za-z0-9_-]+|youtube\.com/watch\?v=[A-Za-z0-9_-]+)", line)`.
  3. The README mermaid block MUST use ```` ```mermaid ```` (lowercase, no language alias). Some renderers accept `mmd`; the gate rejects it for consistency.
  4. The image embed's alt text MUST be non-empty — accessibility (ux-spec §6 Accessibility). An empty `![](...)` is a gate failure.
- Vocabulary discipline (PRD §14): never "court-admissible," "autonomous SOC," "Ralph Wiggum," "replaces L1," "eliminates hallucinations." The README is the highest-visibility surface; the gate is strict here on purpose.
