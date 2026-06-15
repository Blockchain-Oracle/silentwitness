# Story — Ground-truth parsers (NIST Data Leakage PDF, Hacking Case writeups, Nitroba, case-trapdoor)

**ID:** story-ground-truth-parsers
**Epic:** Epic 14 — Accuracy harness + baseline comparison
**Depends on:** story-dataset-manifests, story-common-types
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent preparing the accuracy harness
**I want to** ship `harness/ground_truth/<dataset>_parser.py` for each dataset that emits a typed `list[GroundTruthFinding]` — parsing the public NIST Data Leakage answer-key PDF (`leakage-answers.pdf`), scraping the NIST Hacking Case community writeups (intrinsicode.net + zarat.hatenablog.com), encoding the hand-crafted Nitroba ground truth from the pcap pivot chain, and encoding the synthetic `case-trapdoor` ground truth from its synthesis spec
**So that** the scorer (`story-scorer`) has a single normalised, hash-pinned ground-truth source per dataset to grade both vanilla Protocol SIFT baseline and SilentWitness findings against — making the PRD §4 headline "time-to-handoff-ready-report" and PRD §6 secondary metrics (claim provenance rate, hallucinated-claim count) measurable, not estimated, per Rob T. Lee's honesty rubric (FR11 accuracy harness; judging criterion IR Accuracy).

---

## File modification map

- `harness/ground_truth/__init__.py` — NEW — empty package marker.
- `harness/ground_truth/schema.py` — NEW — Pydantic v2 models. `GroundTruthFinding` fields: `id: str` (e.g., `"GT-NDL-001"`), `dataset_id: Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]`, `category: Literal["user_profile", "installed_tool", "credential", "network_indicator", "timestamp", "file_artifact", "persistence", "exfiltration", "communication", "other"]`, `summary: str` (one-sentence finding, ≤200 chars), `expected_artifact_substrings: list[str]` (≥1, each a verbatim substring that MUST appear in evidence — used by the scorer's HALLUCINATION verification step), `expected_path_globs: list[str]` (optional file-path glob patterns), `supporting_question_id: str | None` (e.g., NIST Data Leakage answer-key question number), `source: Literal["nist_pdf", "community_writeup", "hand_crafted", "synthetic_spec"]`, `source_url: HttpUrl | None`, `source_excerpt: str | None` (verbatim quote from the source, attribution). `model_config = ConfigDict(frozen=True, extra="forbid")`. Module ≤120 LOC.
- `harness/ground_truth/nist_data_leakage_parser.py` — NEW — `parse() -> list[GroundTruthFinding]`. Downloads `https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf` to a cache dir (`~/.cache/silentwitness/ground_truth/`) on first run, verifies a pinned SHA256 (committed in `harness/ground_truth/nist-data-leakage.answer-key-sha256.txt`), then extracts the structured answer block per question using `pypdf` (`pypdf.PdfReader(path).pages[i].extract_text()`). Each numbered question becomes one `GroundTruthFinding` with `supporting_question_id`, `summary`, `expected_artifact_substrings` lifted from the answer's "supported by artifact X at path Y" reference, `source="nist_pdf"`, `source_url` set, `source_excerpt` set to the verbatim answer paragraph (≤500 chars truncated). ≤280 LOC.
- `harness/ground_truth/nist_hacking_case_parser.py` — NEW — `parse() -> list[GroundTruthFinding]`. Scrapes two committed-locally writeup snapshots (NOT live HTTP — committed under `harness/ground_truth/snapshots/` to avoid live-fetch nondeterminism + offline CI): `harness/ground_truth/snapshots/intrinsicode-net-hacking-case.html` and `harness/ground_truth/snapshots/zarat-hatenablog-com-hacking-case.html`. Parses with `beautifulsoup4` (`bs4.BeautifulSoup(html, "html.parser")`), extracts the canonical question-answer pairs (~30 findings total: user profile = Mr. Evil, installed tools = Ethereal/Anonymizer/Cain & Abel/Look@Lan/etc., MAC = `00:02:B3:DD:00:A2`, IP, hostname `N-1A9ODN6ZXK4LQ`, email `whoknowsme@sbcglobal.net`, wardriving evidence, etc.). Each becomes a `GroundTruthFinding` with `source="community_writeup"`, `source_url` set, `source_excerpt` ≤500 chars. ≤300 LOC.
- `harness/ground_truth/nitroba_parser.py` — NEW — `parse() -> list[GroundTruthFinding]`. Hand-crafted ground truth (the official solution PDF is password-gated per evaluation context §A.1). Loads `harness/ground_truth/nitroba.handcrafted.json` (committed) and returns the parsed `GroundTruthFinding` list. The JSON encodes ~8 findings: suspect identification (Johnny Lee Henry per the canonical community-converged answer), MAC + dorm room + class roster pivot, willselfdestruct.com one-shot URL evidence, SMTP-to-Yahoo timing, etc. `source="hand_crafted"`. ≤120 LOC.
- `harness/ground_truth/case_trapdoor_parser.py` — NEW — `parse() -> list[GroundTruthFinding]`. If Epic 15 has shipped the synthetic case, loads `harness/ground_truth/case-trapdoor.synthetic.json` (Epic 15 produces this file). Otherwise returns `[]` and logs `"case-trapdoor not yet synthesised (Epic 15 optional)"`. ≤80 LOC.
- `harness/ground_truth/nitroba.handcrafted.json` — NEW — hand-crafted Nitroba ground truth file (≥6 findings).
- `harness/ground_truth/nist-data-leakage.answer-key-sha256.txt` — NEW — pinned SHA256 of the `leakage-answers.pdf` (single hex line, no newline). Recomputed once on fetch; never auto-mutated.
- `harness/ground_truth/snapshots/intrinsicode-net-hacking-case.html` — NEW — committed HTML snapshot of the writeup (saved verbatim; small, ≤200 KB).
- `harness/ground_truth/snapshots/zarat-hatenablog-com-hacking-case.html` — NEW — committed HTML snapshot of the writeup.
- `harness/ground_truth/snapshots/README.md` — NEW — attribution + fetch-date + license-of-use note for each snapshot (writeups are blog posts; cited under fair-use research; full URL + author attribution preserved).
- `harness/ground_truth/cli.py` — NEW — CLI: `python harness/ground_truth/cli.py <dataset_id>` prints the parsed `GroundTruthFinding` list as JSON, exits 0 on success, 1 if the dataset_id is unknown, 2 if the parser fails (e.g., PDF SHA256 mismatch). ≤80 LOC.
- `pyproject.toml` — UPDATE — add `pypdf>=5.1`, `beautifulsoup4>=4.12`, and `lxml>=5.3` (for `bs4`'s lxml parser) to `[project.dependencies]` (or under the `harness` optional-dependency group if dependency-grouped per the project's existing convention).
- `tests/integration/test_harness_ground_truth_parsers.py` — NEW — ≥7 BDD scenarios: `nist_data_leakage_parser.parse()` returns ≥20 `GroundTruthFinding` objects (the answer key has ≥20 numbered questions); every returned finding has `dataset_id == "nist-data-leakage"` and `source == "nist_pdf"`; every finding has ≥1 `expected_artifact_substring` (no empty-substring findings); `nist_hacking_case_parser.parse()` returns ≥15 findings including one whose `expected_artifact_substrings` contains the MAC `"00:02:B3:DD:00:A2"`; `nitroba_parser.parse()` returns ≥6 findings; `case_trapdoor_parser.parse()` returns `[]` when the synthetic JSON is absent; corrupting the cached `leakage-answers.pdf` (mutate one byte) → next `parse()` raises `SHA256MismatchError`; CLI `python harness/ground_truth/cli.py nist-data-leakage` exits 0 and emits valid JSON parseable into `list[GroundTruthFinding]`. ≥7 tests pass.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given harness/ground_truth/nist-data-leakage.answer-key-sha256.txt is committed
And   the cached leakage-answers.pdf is present (fetched on first run)
When  `uv run python -c "from harness.ground_truth.nist_data_leakage_parser import parse; r = parse(); print(len(r))"` runs
Then  exit code is 0
And   stdout integer is ≥20

Given harness/ground_truth/snapshots/intrinsicode-net-hacking-case.html exists
And   harness/ground_truth/snapshots/zarat-hatenablog-com-hacking-case.html exists
When  `uv run python -c "from harness.ground_truth.nist_hacking_case_parser import parse; r = parse(); macs = [f for f in r if any('00:02:B3:DD:00:A2' in s for s in f.expected_artifact_substrings)]; print(len(macs))"` runs
Then  exit code is 0
And   stdout integer is ≥1 (the MAC ground-truth finding is present)

Given harness/ground_truth/nitroba.handcrafted.json is committed
When  `uv run python -c "from harness.ground_truth.nitroba_parser import parse; r = parse(); print(len(r))"` runs
Then  exit code is 0
And   stdout integer is ≥6

Given harness/ground_truth/case-trapdoor.synthetic.json does NOT exist
When  `uv run python -c "from harness.ground_truth.case_trapdoor_parser import parse; print(len(parse()))"` runs
Then  exit code is 0
And   stdout is "0"

Given the cached leakage-answers.pdf is mutated (byte 0 flipped)
When  the nist_data_leakage_parser.parse() is called
Then  SHA256MismatchError is raised
And   the error message references "answer-key-sha256.txt"

Given `uv run python harness/ground_truth/cli.py nist-data-leakage` runs
When  stdout is captured and json.loads is called on it
Then  the result is a list
And   every item validates against GroundTruthFinding

Given `uv run python harness/ground_truth/cli.py unknown-dataset` runs
Then  exit code is 1
And   stderr contains "unknown dataset_id"

Given tests/integration/test_harness_ground_truth_parsers.py exists
When  `uv run pytest tests/integration/test_harness_ground_truth_parsers.py -v` runs
Then  exit code is 0
And   ≥7 tests pass
```

---

## Shell verification

```bash
# Parser smoke (all four)
uv run python harness/ground_truth/cli.py nitroba | jq -e 'length >= 6'
uv run python harness/ground_truth/cli.py nist-data-leakage | jq -e 'length >= 20'
uv run python harness/ground_truth/cli.py nist-hacking-case | jq -e 'length >= 15'
uv run python harness/ground_truth/cli.py case-trapdoor | jq -e 'length == 0 or length >= 1'

# Tests
uv run pytest tests/integration/test_harness_ground_truth_parsers.py -v

# Strict typing
uv run mypy --strict harness/ground_truth/

# Lint
uv run ruff check harness/ground_truth/

# File-size guard (≤400 LOC per file)
uv run python .pre-commit-hooks/file-size-guard.py harness/ground_truth/*.py

# Coverage floor 85% on harness/
uv run coverage run -m pytest tests/integration/test_harness_ground_truth_parsers.py
uv run coverage report --include="harness/ground_truth/*" --fail-under=85
```

---

## Notes for coding agent

- Reference: `docs/architecture.md` §3 folder layout (`harness/ground_truth/`). `docs/PRD.md` §4 headline metric + §6 secondary metrics (claim provenance rate, hallucinated-claim count — both need ground truth to compute). `docs/PRD.md` §9 dataset choice (PDF/writeup/hand-crafted/synthetic split). `docs/epics.md` Epic 14 DoD ("honest disclosure of NIST Hacking Case memorisation risk per PRD §9"). `docs/CICD_SPEC.md` coverage 85% floor on `harness/*`.
- Reference: `context/evaluation/10-datasets-and-evaluation-methodology.md` §A.1 (Nitroba — community-converged answer, NOT the password-gated PDF; suspect identification + dorm-room + wireless-pivot chain), §A.2 (NIST Data Leakage — **public PDF answer key** at `https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf` with structured numbered questions + per-artifact references), §A.3 (NIST Hacking Case — community writeups at intrinsicode.net 2021-05-19 + zarat.hatenablog.com 2021-12-19).
- **NIST Data Leakage parser strategy:** the `leakage-answers.pdf` has a stable structure — numbered questions followed by "Answer:" + "Supported by:" + "Artifact path:" blocks. Use `pypdf.PdfReader(path)` for text extraction; if `pypdf` produces mangled output (PDFs sometimes break extraction), fall back to `pdfminer.six` (`pdfminer.high_level.extract_text(path)`). Implement `pypdf` first and only add `pdfminer.six` if the extracted text fails the per-question regex (`re.findall(r"^(\d+)\.\s+(.+?)(?=^\d+\.|\Z)", text, re.M|re.S)`). Document the choice in the parser module docstring.
- **NIST Hacking Case parser strategy:** snapshot the writeups locally (`curl -fsSL <wayback-url> > harness/ground_truth/snapshots/<host>.html` ONCE during development), commit the snapshots, parse with BeautifulSoup. Live HTTP at parse-time is brittle and breaks offline CI. The snapshots are small (≤200 KB each); committing them is acceptable per fair-use research norms — `snapshots/README.md` documents attribution + fetch-date.
  - **Intrinsicode writeup URL: use the Wayback Machine snapshot to insulate against the live blog going dark or mutating.** Canonical (live, may rot): `https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/`. **Snapshot-of-record (use this for the curl):** `https://web.archive.org/web/2026/https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/` (Wayback selects the latest available capture). Record the resolved Wayback URL (with timestamp) in `snapshots/README.md` for provenance.
  - Zarat hatena blog URL: `https://zarat.hatenablog.com/entry/2021/12/19/223735` (Hatena Blogs are stable; Wayback also archived).
- **Nitroba parser strategy:** the official solution PDF is password-gated. DO NOT attempt to bypass — encode the community-converged answer chain as a hand-crafted JSON in `harness/ground_truth/nitroba.handcrafted.json`. The JSON is the source of truth; the parser is a pass-through that validates + returns. This is the honest path per PRD §14 vocabulary (we say "hand-crafted from community-converged consensus", we do NOT say "official answer key").
- **case-trapdoor parser:** Epic 15 is OPTIONAL per `docs/epics.md`. The parser must return `[]` gracefully when `case-trapdoor.synthetic.json` is absent. Log a single info line; do NOT raise. The scorer (`story-scorer`) then skips the dataset.
- The `expected_artifact_substrings` field is the HALLUCINATION-verification primitive: the scorer takes each baseline / SilentWitness finding, looks for the GT finding's expected substrings, and if found in the agent's finding AND the substrings also occur in the evidence (verified via `find`/`grep` against the mount), it's a TRUE_POSITIVE. If the agent's claim cites a substring that does NOT exist in the evidence at all, the scorer marks it HALLUCINATION. So substrings must be **verbatim copies of strings present in the evidence** — e.g., for NIST Hacking Case, the MAC is `"00:02:B3:DD:00:A2"` exactly (hex-pair colon-separated, uppercase), the hostname is `"N-1A9ODN6ZXK4LQ"` exactly, the email is `"whoknowsme@sbcglobal.net"` exactly. NOT paraphrases.
- The SHA256 pin on `leakage-answers.pdf` is committed once: `sha256sum /tmp/leakage-answers.pdf | awk '{print $1}' > harness/ground_truth/nist-data-leakage.answer-key-sha256.txt`. **Pre-commit value (verified against the current NIST CFReDS archive copy):** `218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b`. Commit this exact 64-char lowercase hex string (no trailing newline) into `harness/ground_truth/nist-data-leakage.answer-key-sha256.txt`. Expose it from the parser module as `ANSWER_KEY_SHA256 = "218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b"` (module-level constant) so the verification path is one constant — not a file read at every parse. The parser raises `SHA256MismatchError` on mismatch — this protects against silent NIST archive mutation between runs (the archive has moved several times per evaluation context §A.3 known issues).
- Caching: fetched PDFs go to `~/.cache/silentwitness/ground_truth/` (XDG-compliant). Don't re-fetch on every parse — check cache first, fetch only if absent or SHA mismatch.
- The `source_excerpt` field carries the verbatim quote (≤500 chars truncated) for attribution. This is a fair-use requirement — when SilentWitness's accuracy report (PRD §10 deliverable 6) cites ground truth, it must show its sources.
- DO NOT make HTTP calls in tests. Use the committed snapshots for NIST Hacking Case. For NIST Data Leakage, mock the PDF download in tests OR pre-cache the PDF in the test fixture (preferred — tests fetch once on the first CI run, cache survives subsequent runs).
- Vocabulary discipline (PRD §14): never "court-admissible". Use "ground truth" not "correct answer". Use "community-converged" not "verified" for the Nitroba hand-crafted entries. Use "verbatim substring" not "literal string match".
- Library docs to consult via Context7 BEFORE coding:
  - `pypdf` topic `PdfReader extract_text page iteration v5` (the v3 → v5 API differs significantly).
  - `beautifulsoup4` topic `BeautifulSoup html parser select_one find_all` (use `html.parser` not `lxml` for the default test env; switch to `lxml` only if the HTML is malformed).
  - (Optional fallback) `pdfminer.six` topic `extract_text high_level`.
- Known pitfalls:
  1. `pypdf` text extraction on multi-column PDFs can interleave columns — the `leakage-answers.pdf` is single-column, so this should not bite, but verify with a manual diff of the first page's extracted text against the visual PDF before trusting the parse.
  2. BeautifulSoup `find_all("p")` returns paragraphs in DOM order, which usually matches reading order on simple blog templates. Verify the parser handles both writeup site templates separately — they have different DOM shapes.
  3. SHA256 pin must be exact 64 hex chars, lowercase. `sha256sum` outputs lowercase by default; don't accidentally uppercase it.
  4. `case-trapdoor` parser MUST NOT crash if Epic 15 hasn't shipped. The integration test asserts the empty-return behaviour.
  5. Coverage 85% floor: the NIST Hacking Case parser is the largest LOC contributor (~300). Cover both writeup-site templates + the merge-deduplication logic that combines findings from the two sites.
