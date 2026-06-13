# Pre-submission checklist (run before pressing Submit on Devpost)

Every box below must be green before the submission is pressed. The
`scripts/check_submission_ready.py` gate verifies every machine-checkable
row; the manual rows ("video plays in incognito", "form fields match the
mapping") are documented so a teammate audit can re-run them in <5 minutes.

> The `## Banned-vocab references below` section at the bottom intentionally
> mentions the §14 banned terms (court-admissible, autonomous SOC,
> Ralph Wiggum) because this file IS the documentation of the gate. The
> §14 vocab scanner carves out this file by path so the meta-discussion
> doesn't trip the gate on itself.

## Machine-verifiable

- [ ] CI green on `main` — `gh run list --branch main --limit 1 --json status,conclusion --jq '.[0]'` reports `{"status":"completed","conclusion":"success"}`
- [ ] All 8 PRD §10 deliverables present — `uv run python scripts/check_submission_ready.py --mode deliverables` exits 0
- [ ] No `mock` / `fake` / `dummy` / `hardcoded` in `src/` — `git grep -iE '(mock|fake|dummy|hardcoded)' src/ | grep -vE '(test|\\bMockType\\b)' | wc -l` reports 0 (CICD_SPEC §14 gate; legitimate `Mock` type imports in tests are carved out)
- [ ] LICENSE file is MIT — `uv run python scripts/check_submission_ready.py --mode license` exits 0
- [ ] No PRD §14 banned vocab anywhere in committed `src/` + `docs/` — `uv run python scripts/check_submission_ready.py --mode vocab` exits 0 (carve-out: this file, PRD.md, CICD_SPEC.md)
- [ ] README's `<!-- DEMO_VIDEO_URL -->` placeholder has been swapped for a real URL — `uv run python scripts/check_submission_ready.py --mode placeholder-swap` exits 0
- [ ] `docs/EXAMPLE_EXECUTION_LOGS/` deterministic regeneration test passes — `uv run pytest tests/integration/test_example_execution_logs.py` exits 0
- [ ] `NOTICES.md` present at repo root with required H2 sections — `test -s NOTICES.md && uv run pytest tests/unit/test_build_notices.py` exits 0
- [ ] Demo video URL well-formed (manual after recording) — `uv run python scripts/check_submission_ready.py --mode video-url --video-url <url>` exits 0; URL pattern `https://youtu.be/<11-char-id>` or `https://www.youtube.com/watch?v=<11-char-id>`

## Manual (judge-facing reality check)

- [ ] Demo video plays in incognito Chrome + incognito Firefox + Safari private window
- [ ] All `docs/*.md` links resolve (no broken `./X.md` references): `grep -rEo '\\./[A-Z_]+\\.md' docs/ | sort -u` — each path must exist
- [ ] Gallery preview on Devpost (pre-submit preview button) shows: title `SilentWitness`, tagline = PRD §1 one-liner, project story = `docs/DEVPOST.md` content rendered correctly, video thumbnail visible

## Devpost form field mapping (copy from `docs/DEVPOST.md`)

| Devpost field | Source |
|---|---|
| Project title | `SilentWitness` (exact, no taglines) |
| Tagline | PRD §1 verbatim one-liner |
| Project story | `docs/DEVPOST.md` body verbatim (the Markdown renders) |
| Built-with tags | `docs/DEVPOST.md` §"Built with" comma list |
| Demo video URL | YouTube Unlisted URL from the demo-recording session |
| Repository URL | `https://github.com/Blockchain-Oracle/silentwitness` |
| Try-It-Out URL | `https://github.com/Blockchain-Oracle/silentwitness/blob/main/docs/TRY_IT_OUT.md` |

## Order of operations

1. Run `uv run python scripts/check_submission_ready.py --mode all` — fix anything red.
2. Record the demo video; upload as YouTube Unlisted; copy the URL.
3. Run `uv run python scripts/swap_demo_video_url.py <url>` — swaps the placeholder in README.md + docs/TRY_IT_OUT.md.
4. Commit with `docs(submission): swap demo video URL` and push to `main`.
5. Re-run `uv run python scripts/check_submission_ready.py --mode all` — every box must be green.
6. On Devpost: press "Preview" — verify title + tagline + story + video thumbnail.
7. Press Submit. Paste the form fields from the mapping table above.
8. Open the gallery preview in incognito; play the video; click each docs link in the project story.

## Banned-vocab references (carve-out documentation)

This file's `scripts/check_submission_ready.py` gate excludes itself, `docs/PRD.md`, `docs/CICD_SPEC.md`, and the per-doc gate scripts from the banned-vocab scan. The reason: each of those files documents the banned list itself (the PRD §14 row, the CICD §14 gate, the per-doc tuples). The list itself, for reader reference:

> Banned per PRD §14: "court-admissible", "autonomous SOC", "Ralph Wiggum",
> "replaces L1", "eliminates hallucinations". Banned per CLAUDE.md non-negotiable:
> the same five plus "find evil" as marketing copy (the literal hackathon
> name "Find Evil!" with the `[](link)` form is carved out).
