# Story — Devpost submission (final form fields, demo video URL swap, pre-submission checklist, gallery preview verification)

**ID:** story-devpost-submission
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-readme-polish, story-architecture-diagram-png, story-accuracy-report-writeup, story-dataset-doc, story-try-it-out-doc, story-execution-logs-export, story-ci-workflows, story-scaffold-uv-pyproject (LICENSE)
**Estimate:** ~2h (most of the time is video editing + form filling — coding-agent scope is checklist + helper script)
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent driving the final Devpost submission
**I want to** ship `docs/devpost-submission-checklist.md` (the pre-submit gate every box must be green before pressing Submit on Devpost), `docs/DEVPOST.md` (the Markdown source of the project-story field; the Devpost web form accepts the Markdown verbatim), `scripts/check_submission_ready.py` (the CI-callable gate that confirms every deliverable is present and the README's demo-video URL placeholder has been swapped for a real URL), and a one-shot `scripts/swap_demo_video_url.py` to substitute the YouTube unlisted URL into `README.md` + `docs/TRY_IT_OUT.md` at submission time
**So that** the Devpost Rules §4 deliverables (`MUST`s 1-8 from PRD §10) ship green; the pre-submission checklist below is verifiable end-to-end by a teammate audit per epics.md Epic 16 DoD; and the final submission shows up in the Devpost gallery with the correct title, pitch, story, built-with tags, video URL, and repo URL — no broken links, no placeholders, no banned vocabulary anywhere in the committed artifacts (PRD §14 + CICD_SPEC §14).

---

## File modification map

- `docs/DEVPOST.md` — NEW — Markdown source for the Devpost project-story field. Sections (the Devpost form accepts Markdown verbatim):
  1. `# SilentWitness` — H1 matches project title verbatim.
  2. `## One-line pitch` — quoted verbatim from PRD §1: *"SilentWitness — a hypothesis-first DFIR investigator whose report writes itself, with every claim locked to the tool that produced it."*
  3. `## What it does` — adapted from PRD §1 + §6: 3-paragraph narrative (the user pain → the architectural answer → the demo arc summary).
  4. `## Inspiration` — adapted from `research/protocol-sift-2026/refs/quotes-for-pitch.md` §G.1 (Rob T. Lee's "command-line stenographer" quote + the 2-3 evening report-writing hours; the GTG-1002 framing from PRD §2).
  5. `## How we built it` — table mirroring architecture §1 stack-table (Python 3.12, uv 0.11.18, ruff, mypy, Pydantic v2, FastMCP ≥1.23, Pydantic AI ≥1.105, Volatility 3 2.27.0 in own venv, rich, hypothesis property tests, WeasyPrint ≥68.1, mistune ≥3.2.1, spaCy NER, HMAC-SHA256 PBKDF2-600k — note: `structlog` was dropped per audit Decision A in favor of direct Pydantic `model_dump_json()`); 2-paragraph narrative on the hypothesis-pivot loop + the citation/entity gates.
  6. `## Challenges we ran into` — 3 bullets: pinning to SIFT 2026's tool versions; making the entity gate work across Volatility 3 stdout shapes; reaching the 95% coverage floor on `verification/` per CICD_SPEC §6.
  7. `## Accomplishments that we're proud of` — 3 bullets: measured Δ vs vanilla Protocol SIFT baseline (PRD §4 headline metric); 22 typed MCP tools across 5 forensic families; HMAC-signed approval ledger with PBKDF2-SHA256 at 600k iterations.
  8. `## What we learned` — adapted from `research/protocol-sift-2026/refs/quotes-for-pitch.md` §G.3 (the "honesty over polish" framing — what worked vs what didn't on the memorization-risk dataset).
  9. `## What's next for SilentWitness` — PRD §7 out-of-scope list reframed as roadmap (live-host triage via Velociraptor MCP; multi-case management; cloud forensics).
  10. `## Built with` — Markdown checklist matching the Devpost "built-with" tags exactly: `python`, `pydantic-ai`, `mcp`, `fastmcp`, `volatility-3`, `sift-workstation`, `claude`, `docker`, `weasyprint`. (Devpost's tag input is comma-separated; this section documents the canonical list — the human typing them into the form copies from this section.)
  11. `## Try it yourself` — pointer to `docs/TRY_IT_OUT.md` + the 3-command native install.
  12. `## License` — MIT callout.
  Total ≤400 lines.
- `docs/devpost-submission-checklist.md` — NEW — operator-facing pre-submission checklist, ≤200 lines. Section: `# Pre-submission checklist (run before pressing Submit on Devpost)`. Then a verbatim Markdown checklist (the box list is the load-bearing artifact — the coding agent's job is to make every box machine-verifiable via the gate script below):
  - [ ] CI green on `main` (verified via `gh run list --branch main --limit 1 --json status,conclusion`)
  - [ ] All 8 PRD §10 deliverables present (verified via `scripts/check_submission_ready.py --deliverables`)
  - [ ] No `mock` / `fake` / `dummy` / `hardcoded` in `src/` (verified via the §14 grep; CICD_SPEC §14 gate)
  - [ ] Demo video URL works in incognito mode (verified manually via `scripts/check_submission_ready.py --video-url <url>` which makes an unauthenticated HEAD request; documents the manual cross-browser check)
  - [ ] LICENSE file is MIT (verified via `grep -c '^MIT License' LICENSE`)
  - [ ] No `Ralph Wiggum` / `autonomous SOC` / `court-admissible` vocab in any committed file (verified via repo-wide `grep -riE`)
  - [ ] README's `<!-- DEMO_VIDEO_URL -->` placeholder has been swapped for a real URL (verified by `grep -F 'PLACEHOLDER' README.md` returning zero matches)
  - [ ] `docs/EXAMPLE_EXECUTION_LOGS/` deterministic regeneration test passes (verified via the integration test from story-execution-logs-export)
  - [ ] `NOTICES` file present at repo root (license attribution for Hayabusa, Chainsaw, Velociraptor, Suricata, Vol3, EZ Tools, Pydantic AI, MCP, FastMCP, WeasyPrint, spaCy, etc.) — verified via `test -s NOTICES.md` and `scripts/check_submission_ready.py --notices` (delegated to `story-third-party-notices`)
  - [ ] Devpost form fields filled (verified manually — checklist documents the field-to-source mapping):
    - Project title: `SilentWitness` (exact, no taglines)
    - Tagline: PRD §1 verbatim one-line pitch
    - Project story: copied from `docs/DEVPOST.md` verbatim
    - Built-with tags: copied from `docs/DEVPOST.md` §"Built with" verbatim
    - Demo video URL: the YouTube unlisted URL produced by the demo-recording session
    - Repository URL: `https://github.com/<org>/silentwitness`
    - Try-it-out URL: `https://github.com/<org>/silentwitness/blob/main/docs/TRY_IT_OUT.md`
  Then a final section `## Order of operations` documenting the submission sequence:
  1. Run `scripts/check_submission_ready.py` — fix anything red.
  2. Record the demo video; upload as YouTube Unlisted; copy the URL.
  3. Run `scripts/swap_demo_video_url.py <url>` — swaps the placeholder; commits the change with conventional message `docs(submission): swap demo video URL`.
  4. Re-run `scripts/check_submission_ready.py` — every box green.
  5. Press Submit on Devpost; paste form fields from the mapping above.
  6. Verify gallery preview in incognito; check video plays; check links resolve.
- `scripts/check_submission_ready.py` — NEW — ≤300 LOC Python CLI gate. Modes: `--all` (default), `--deliverables`, `--vocab`, `--video-url <url>`, `--license`, `--placeholder-swap`. Each mode prints `✓` or `✗` per checked rule + exits 0 if all pass, 1 if any fail. Deliverable checks (rules §4) map to the 8 PRD §10 rows:
  1. Public GitHub repo + LICENSE MIT → file exists + starts with `MIT License`
  2. Demo video → README contains a `youtu.be/` or `youtube.com/watch` URL (NOT the placeholder) within first 100 lines
  3. Architecture diagram → `docs/architecture.md` exists AND `docs/diagrams/architecture.svg` exists AND README contains a ```` ```mermaid ```` fenced block
  4. Devpost write-up → `docs/DEVPOST.md` exists + total line count ≤400 + contains literal "Built with" heading
  5. Dataset documentation → `docs/DATASETS.md` exists + `harness/datasets/*.manifest.json` count ≥3 (Nitroba + NIST x2; case-trapdoor optional)
  6. Accuracy report → `docs/ACCURACY_REPORT.md` exists (story-accuracy-report-writeup)
  7. Try-It-Out instructions → `docs/TRY_IT_OUT.md` exists + contains literal `curl --proto` AND `docker compose up`
  8. Agent execution logs → `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/` directory exists + `report.md` exists with both `## Gaps` and `## Appendix-Audit` sections
- `scripts/swap_demo_video_url.py` — NEW — ≤80 LOC. Takes `<url>` as positional arg. Validates the URL matches `^https://youtu\.be/[A-Za-z0-9_-]{11}$` OR `^https://(www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]{11}(&.*)?$`. If valid, performs an in-place atomic-rename swap of the literal `https://youtu.be/PLACEHOLDER` and `<!-- DEMO_VIDEO_URL -->` markers in `README.md` + `docs/TRY_IT_OUT.md`. Refuses if either marker is missing (probably already swapped — refuse-by-default rather than overwrite). Prints a summary of which files changed; exit 0 on success.
- `tests/unit/test_submission_ready.py` — NEW — ≥8 BDD scenarios via subprocess against `scripts/check_submission_ready.py` + `scripts/swap_demo_video_url.py` with fixture trees:
  - `--all` against a clean fixture tree → exit 0;
  - `--deliverables` against a tree missing `docs/DATASETS.md` → exit 1 with stderr "deliverable 5: dataset documentation missing";
  - `--vocab` against a tree containing the literal `court-admissible` anywhere → exit 1;
  - `--license` against a non-MIT LICENSE → exit 1;
  - `--placeholder-swap` against a README still containing `https://youtu.be/PLACEHOLDER` → exit 1;
  - `--video-url https://youtu.be/aaaaaaaaaaa` (valid 11-char ID) → exit 0;
  - `--video-url https://example.com/video.mp4` (not YouTube) → exit 1;
  - `swap_demo_video_url.py https://youtu.be/aaaaaaaaaaa` against a fixture with placeholders → replaces in both files; re-running → refuses (no placeholder remaining).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given docs/DEVPOST.md is committed
When  `wc -l docs/DEVPOST.md` runs
Then  the line count is ≤ 400

Given docs/DEVPOST.md is committed
When  `grep -c '^## ' docs/DEVPOST.md` runs
Then  the integer is ≥ 9 (one-line pitch + 8 form-mapped sections)

Given docs/DEVPOST.md is committed
When  `grep -F '## Built with' docs/DEVPOST.md` runs
Then  exit code is 0

Given docs/devpost-submission-checklist.md is committed
When  `grep -c '^- \[ \]' docs/devpost-submission-checklist.md` runs
Then  the integer is ≥ 8

Given the pre-submission checklist contains the literal "CI green on main" line
When  `grep -F 'CI green on main' docs/devpost-submission-checklist.md` runs
Then  exit code is 0

Given the pre-submission checklist contains the literal "No mock/fake/dummy/hardcoded" line
When  `grep -F 'mock' docs/devpost-submission-checklist.md` runs
Then  exit code is 0
And   `grep -iE '(Ralph Wiggum|autonomous SOC|court-admissible)' docs/devpost-submission-checklist.md` returns ≥ 1 match (the checklist references the banned vocab list — this is intentional; the checklist is itself the documentation of the gate; the §14 vocab gate carves out paths that document the banned-vocab list, anchored to `docs/devpost-submission-checklist.md` + `docs/PRD.md` + `docs/CICD_SPEC.md`)

Given `uv run python scripts/check_submission_ready.py --deliverables` runs against the committed tree
When  every deliverable is present
Then  exit code is 0
And   stdout shows 8 lines, each starting with "✓"

Given a clean fixture tree with the placeholder still in README.md
When  `uv run python scripts/swap_demo_video_url.py https://youtu.be/aaaaaaaaaaa` runs against the fixture
Then  exit code is 0
And   the fixture README contains "https://youtu.be/aaaaaaaaaaa"
And   the fixture README does NOT contain "PLACEHOLDER"

Given the fixture README no longer contains the placeholder
When  the swap script is re-run with the same URL
Then  exit code is 1
And   stderr contains "no placeholder marker found"

Given tests/unit/test_submission_ready.py exists
When  `uv run pytest tests/unit/test_submission_ready.py -v` runs
Then  exit code is 0
And   ≥8 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/unit/test_submission_ready.py -v

# Strict typing
uv run mypy --strict scripts/check_submission_ready.py scripts/swap_demo_video_url.py

# Lint
uv run ruff check scripts/check_submission_ready.py scripts/swap_demo_video_url.py

# §14 vocab gate clean on DEVPOST.md (the only doc that does NOT carve out the banned vocab — DEVPOST is judge-facing)
grep -iE '(court-admissible|Ralph Wiggum|autonomous SOC|replaces L1|eliminates hallucinations)' docs/DEVPOST.md && exit 1 || true

# Pre-submission gate (runs the full checklist programmatically)
uv run python scripts/check_submission_ready.py --all
```

---

## Notes for coding agent

- Reference: `docs/PRD.md` §10 (the 8 mandatory deliverables list) + §11 (README shape) + §14 (vocabulary discipline); `docs/architecture.md` §1 (stack table — the "Built with" section mirrors this); `research/protocol-sift-2026/refs/quotes-for-pitch.md` §G.1/G.2/G.3 (Inspiration, What it does, What we learned narratives — adapt verbatim); `docs/epics.md` Epic 16 DoD ("Devpost submission confirmed; demo video published + embedded; rules §4 deliverable checklist passes a teammate audit"); `docs/CICD_SPEC.md` §14 (no-mock/no-fake gate — `docs/devpost-submission-checklist.md` documents the gate, which is the documented carve-out for that file's references to banned vocab tokens).
- **Banned-vocab carve-out (load-bearing detail):** the pre-submission checklist itself references the banned vocab strings (e.g., the line `No Ralph Wiggum / autonomous SOC / court-admissible vocab in any committed file`). This is the intentional and only acceptable place those tokens appear in committed files — the checklist is documenting the rule. The repo-wide `grep -iE` in CI MUST carve out exactly: `docs/devpost-submission-checklist.md`, `docs/PRD.md`, `docs/CICD_SPEC.md`, `docs/BRAINSTORM.md`, `docs/epics.md`, `docs/architecture.md`, `docs/stories/` (stories reference the rules), and `tests/fixtures/` (fixtures intentionally contain bad-vocab samples to test the gate). Every OTHER committed file MUST have zero matches. The CI gate (`.github/workflows/ci.yml` per CICD_SPEC §4) implements this carve-out via `grep --exclude-dir=docs/stories --exclude=docs/PRD.md ...`; this story documents the carve-out in `scripts/check_submission_ready.py --vocab`.
- **DEVPOST.md is judge-facing:** unlike the checklist, DEVPOST.md has ZERO banned vocab. Verified by the shell verification gate above. This is the artifact that lands in the Devpost gallery preview verbatim.
- **Built-with tags match Devpost taxonomy:** Devpost auto-suggests tags from a controlled vocabulary. Test the tag list (`python`, `pydantic-ai`, `mcp`, `fastmcp`, `volatility-3`, `sift-workstation`, `claude`, `docker`, `weasyprint`) against Devpost's tag picker before the final paste. If any tag is not in the vocabulary, document the closest match in `docs/DEVPOST.md` and DO NOT silently swap.
- **Demo video URL discipline:** the YouTube unlisted URL produced by the demo-recording session is the canonical source. The placeholder `https://youtu.be/PLACEHOLDER` ships in `README.md` + `docs/TRY_IT_OUT.md` via story-readme-polish + story-try-it-out-doc; `scripts/swap_demo_video_url.py` performs the one-shot swap as the LAST commit before submission (conventional-commit message `docs(submission): swap demo video URL`). The swap script refuses to run twice — protects against accidentally overwriting a real URL with a different one.
- **Pre-submission gate is a gate, not a generator:** `scripts/check_submission_ready.py` reads, asserts, exits 0/1. It does NOT mutate. Same pattern as `scripts/check_readme_gate.py` + `scripts/build_datasets_doc.py` + `scripts/check_try_it_out.py`.
- **Order of operations matters:** the checklist enforces a sequence (CI green → record video → swap placeholder → re-verify → submit → verify gallery). Skipping `re-verify` after the swap is the easiest way to ship a broken `README.md` (e.g., if the swap accidentally corrupts the file). The CI gate runs on the submission branch and proves the swap completed correctly.
- **YouTube URL validation regex:** `^https://youtu\.be/[A-Za-z0-9_-]{11}$` matches the 11-char YouTube video ID. Long-form URLs (`youtube.com/watch?v=...`) are also accepted but with the additional `&t=...` query-param suffix tolerated. The validator must reject `vimeo.com`, `loom.com`, `drive.google.com` — the rules §4 demo video is YouTube unlisted (PRD §10 deliverable 2). If the team chose Loom instead, document the swap in the PRD before submission.
- **Repo URL discipline:** the repo URL pasted into Devpost must match `https://github.com/<org>/silentwitness` verbatim; the `<org>` placeholder is filled at submission time. The pre-submission checklist documents the exact paste target.
- **PR-vs-merge:** the submission commits happen on `main` directly via a single PR merged just before submission. The CI gate runs on the PR; merge happens only after green. No force-push, no amend — match the project's git-safety protocol.
- Vocabulary discipline (PRD §14): never "court-admissible" in `docs/DEVPOST.md`; never "autonomous SOC"; never "Ralph Wiggum Loop"; never "replaces L1"; never "eliminates hallucinations". The pre-submission checklist is the documented carve-out for those tokens (it's literally listing the banned terms as a CI assertion).
- Library docs to consult via Context7 BEFORE coding:
  - `httpx` topic `HEAD request + response status code check` (for the optional `--video-url` reachability check; only HEAD, not GET — minimises network footprint).
  - `pydantic` topic `URL validation HttpUrl + custom pattern` (the YouTube URL validator can use `HttpUrl` + a `pattern` constraint, but a plain `re` match is simpler — pick simpler).
- Known pitfalls:
  1. Devpost auto-strips whitespace in form fields — paste-from-Markdown preserves intent best if you keep paragraphs separated by exactly one blank line (no double-blanks). The `## What it does` section is the most prose-dense; verify the rendered preview after paste.
  2. YouTube Unlisted URLs are NOT private — anyone with the link can watch. Document this in the demo-recording playbook (not this story's scope; mention in checklist).
  3. Devpost's gallery preview caches aggressively. After submission, verify in an incognito window without prior Devpost login. The checklist documents this.
  4. The `<!-- DEMO_VIDEO_URL -->` comment marker is what `scripts/swap_demo_video_url.py` keys on; do NOT remove it during README polish — the placeholder serves dual duty as the human-readable note + the machine-readable swap target.
  5. The Devpost submission deadline is 2026-06-15 23:45 EDT (PRD header). Build a 2-hour safety margin; submit by 21:45 EDT to avoid 11th-hour platform issues.
