# Misc Python libs — Deep Verification

**Audit date:** 2026-06-03
**Auditor:** deep-audit research agent (Opus 4.7, 1M context)
**Scope:** All Python runtime + harness libraries referenced in `docs/stories/story-*.md`. Cross-checked against authoritative sources (PyPI, GitHub Releases, project changelogs, vendor docs) as of audit date.
**Method:** PyPI release history + GitHub release notes + Context7 docs query + open-issue review + CVE feeds + source-of-truth (Hugging Face for model artifacts).

> TL;DR — Of 14 libraries audited: **5 spec-claim adjustments needed**, **3 BLOCKERS** (uv version pin, mistune CVEs in spec'd version, regipy can't write registry hives), the spaCy debate **lands on KEEP-but-justify** (regex residual still leaves ~15% F1 floor on people/orgs we genuinely want), and the WeasyPrint anchor-link story holds (clickable `#anchor` href in PDFs is a documented WeasyPrint feature — verified).

---

## Per-library verdict + pin recommendation

| # | Library | Current stable (2026-06-03) | Spec claim | Verdict | Recommended pin | Risk |
|---|---|---|---|---|---|---|
| 1 | **WeasyPrint** | **69.0** (2026-06-02 — yesterday) | "60.x+, A4 PDF, clickable `#audit-<id>` anchors, native deps pango/harfbuzz/cairo" | **FIX-IT** — pin range wrong | `weasyprint>=68.1,<70.0` | Spec pins `>=60,<62`, which is **18 months old + missing CVE-2025-68616 + CVE-2026-49452**. v69.0 is 1 day old → too fresh for prod. Pin v68.1 floor + v70.0 ceiling. |
| 2 | **spaCy + en_core_web_lg** | spaCy **3.8.14** (2026-03-29); model **MIT-licensed**, ~789 MB on disk, F1 0.854 on OntoNotes NER | "3.8+ NER, en_core_web_lg MIT, ~750 MB" | **KEEP** with caveat | `spacy>=3.8.10,<3.9` + `en_core_web_lg==3.8.0` | License OK (MIT confirmed). Spec's 750 MB figure is slightly under-stated (actual 789 MB download / 741 MB install). spaCy 4.0 still pre-release; 3.8.x is the right line. **NO** drop-spacy — see debate §3 below. |
| 3 | **structlog** | **25.5.0** (2025-10-27) | "24+ JSONL audit logging" | **KEEP** with pin bump | `structlog>=25.4,<26` | Spec pins `24+`, but `25.x` brings Python 3.13.4/3.14 isEnabledFor backport that matters for ourLog-level gating. One deprecation: `pad_event → pad_event_to` in `ConsoleRenderer`. We don't use that. Note: **we likely don't NEED structlog**. See §5 below. |
| 4 | **Typer** | **0.26.6** (2026-06-02) | "0.15+ supports Rich integration" | **KEEP** with pin bump | `typer>=0.20,<0.27` | Spec pins `0.15+` which is correct as a floor but stale by 10 minor versions. `0.26.x` has stabilized the Rich integration, fixed `--help` rendering bugs. No breaking changes that affect us. |
| 5 | **mistune** | **3.2.1** (2026-05-03) | "mistune 3+ with `escape=False` + `plugins=[table, url, strikethrough]`" | **BLOCKER → FIX-IT** | `mistune>=3.2.1,<4` | **3.2.0 and earlier had FOUR live CVEs**: CVE-2026-44708 (math plugin XSS), 44896 (figclass XSS), 44897 (heading ID injection), 44899 (image directive CSS injection), 33441 (DoS), 33079 (ReDoS in LINK_TITLE_RE). All patched in **3.2.1**. Spec's "mistune 3+" floor lets the resolver pick 3.1.x which is vulnerable. Floor **must** be 3.2.1. See §4 on `escape=False`. |
| 6 | **httpx** | **0.28.1** (2024-12-06) — still latest stable | "httpx 0.27+" | **KEEP** with pin bump | `httpx>=0.28,<0.29` | Pinned floor stale by one minor. v1.0 is in dev (`1.0.dev3` Sept 2025) but not shipped. 0.28 has been stable for ~18 months. No breaking changes mid-0.28.x. |
| 7 | **hypothesis** | **6.151.11** (2026-04-05) | "hypothesis 6+" | **KEEP** | `hypothesis>=6.140,<7` | Spec's `6+` floor is correct but loose. Latest is 6.151.x; pin a recent floor to avoid CVE-fix lag. No 7.0 in sight. |
| 8 | **uv** | **0.11.18** (2026-06-01) | "uv 0.5+" | **BLOCKER — VERSION SLIP** | `uv==0.11.18` (Dockerfile); `requires-uv >= "0.11"` in `pyproject.toml` | Spec's "uv 0.5+" + story-docker-baseline's pinned `uv 0.5.11` is **17 minor versions stale**. uv has had **multiple breaking semantics changes**: `uv venv --clear` now required, multiple `default=true` indexes now error, lockfile `exclude-newer` semantics changed, alternative-impl Python names changed. The `0.5.11` pin in CICD_SPEC §11.1 is a **hard break risk** if dependent stories assume current uv defaults. |
| 9 | **pytest** | **9.0.3** (2026-04-07) | "pytest 8+" | **KEEP** with floor bump | `pytest>=9.0,<10` | pytest 9.0 is the current line. v9.0.0 introduced TOML config native support + a (now-default-off) terminal progress feature. No breaking change for our test layout. |
| 10 | **rich** (transitive via Typer) | **15.0.0** (2026-04-12) | "rich.live.Live nested layouts work" | **KEEP** — verified working | `rich>=14.1,<16` | v15.0.0 dropped Python 3.8 support (fine, we're on 3.12). **Bonus:** v15.0.0 explicitly fixed nested Live objects — exactly the pattern story-cli-investigate HUD uses. No risk. |
| 11 | **WeasyPrint native dep matrix** | Pango ≥1.44, current `libpango-1.0-0`, `libharfbuzz0b`, `libharfbuzz-subset0`, `libpangoft2-1.0-0`, `libffi8` — all in `python:3.12-slim-bookworm` apt | "pango / harfbuzz / cairo baked in Dockerfile" | **FIX-IT** | See §11 below | story-docker-baseline lists `libffi8` and `shared-mime-info` but **omits `libharfbuzz-subset0`** which is explicitly required in WeasyPrint 68+. Also: **base image must be `python:3.12-slim-bookworm`, not bare `python:3.12-slim`** — the floating slim tag drifts to trixie/forky and breaks the pinned apt names. |
| 12 | **pypdf** | **6.12.2** (2026-05-26) | "pypdf works for text extraction" | **KEEP** | `pypdf>=6.10,<7` | Pure Python, Python ≥3.9. `PdfReader(...).pages[i].extract_text()` is the documented pattern, matches story-report-pdf-export tests verbatim. No breaking changes in 6.x. |
| 13 | **matplotlib** | **3.10.9** (2026-04-24) | "matplotlib==3.10.x" | **KEEP** | `matplotlib>=3.10,<3.11` | Spec's minor-pin discipline is right (PNG-byte-stability for the demo chart). 3.10.9 is the current 3.10.x tip. Agg backend stable. The spec's `Agg` + `defer-import` pattern is correct. |
| 14 | **pytsk3 + pefile + python-evtx + regipy** | pytsk3 20260520; pefile 2024.8.26; python-evtx 0.8.1 (read-only); **regipy 6.2.1 (read-only)** | "all install on SIFT 2026, used for hive write + EVTX write" | **BLOCKER** | See §14 below | **regipy is READ-ONLY** — spec assumes it can write a registry hive. **python-evtx is also READ-ONLY.** Two of the five `synth_*` functions in story-case-trapdoor-synthesis can't be implemented as spec'd. Story-case-trapdoor-synthesis is **OPTIONAL** (Epic 15 cuttable per PRD §9), so this is a "cut or rewrite" decision, not a critical-path blocker. |

---

## High-risk libraries (spec adjustment required)

### §1 — WeasyPrint version pin is stale (FIX-IT, P1)

**Spec note in story-report-pdf-export.md line 152:** *"pin to `>=60,<62` in `pyproject.toml`"*

**Reality:**
- WeasyPrint 69.0 shipped 2026-06-02 (one day ago).
- The 60.x series shipped Nov 2023 and is **18 months obsolete**.
- v68.0 (2026-01-19) introduced a security fix (CVE-2025-68616, URL fetcher redirect handling) — pinning to v60 ships a known-vuln version.
- v69.0 (2026-06-02) closed CVE-2026-49452 (CSS injection via presentational hints).
- The `default_url_fetcher()` function was deprecated in v68.0 and replaced by a `URLFetcher` class; pinning v60.x freezes us on the deprecated path.

**API surface that we actually depend on:**
- `weasyprint.HTML(string=..., base_url=...).write_pdf(target=..., stylesheets=[weasyprint.CSS(string=...)])` — **stable since v52**. Untouched in v68→69.
- Internal anchor links (`<a href="#audit-<id>">` → jump to `<h3 id="audit-<id>">`) — **explicitly documented stable feature** (Context7 ref: "WeasyPrint's PDF files can include hyperlinks, bookmarks…internal (e.g., `<a href="#pdf">`)…become clickable in PDF viewers"). Issue #2655 (anchor name with `(`) was closed `not planned` Jan 2026 — doesn't affect our audit-id slugs (kebab-case alphanumeric, no parens).
- Bookmarks from `<h1>...<h6>` — auto-generated, useful for the PDF outline sidebar.

**Recommendation:**
```toml
weasyprint = ">=68.1,<70.0"
```
v68.1 floor catches CVE-2025-68616 + still-working `default_url_fetcher` if any code path leans on it; v70 ceiling prevents auto-upgrade past the just-shipped v69.0 release before we test. Roll forward to `>=69,<71` after one CI green cycle on v69.0.

**Action items for story-report-pdf-export.md:**
- Line 152: replace `>=60,<62` → `>=68.1,<70.0`.
- Line 137 shell smoke: keep `import weasyprint; print(weasyprint.__version__)` — sanity check is fine.
- Line 173 Context7 hint: add a note that v68+ deprecates `default_url_fetcher` (we don't use it; story-report-pdf-export passes the local `case_dir` as `base_url`, which is the right pattern).

**Open WeasyPrint issues that touch us:**
- #2782 (fontconfig 2.18.0 breaks font matching on macOS Apple Silicon — **not a Docker / Linux issue**; affects dev-on-mac only). Workaround: pin fontconfig 2.17.1 in homebrew. Document in README troubleshooting.
- #2730 (page-margin box default text-align) — cosmetic on header/footer; doesn't affect our title page / body.
- #1092 (table row height with fixed height) — open since 2020; we use tables minimally (timeline section only); accept the risk.

---

### §2 — spaCy + en_core_web_lg pin discipline (KEEP, P2)

**Spec assumption (story-entity-gate.md line 119):** *"spaCy load is expensive (~750MB model, ~3s first load)"*

**Reality:**
- spaCy current = **3.8.14** (2026-03-29). Spec's `3.8+` floor is correct.
- en_core_web_lg current = **3.8.0** (paired with spacy 3.7.2–3.8.x), license **MIT** (confirmed via Hugging Face metadata).
- Model size: actually **789 MB download / 741 MB installed** (varies). Spec's ~750 MB is fine.
- F1 on OntoNotes NER: 0.854 (precision 0.852, recall 0.857).
- 18 NER labels: `CARDINAL, DATE, EVENT, FAC, GPE, LANGUAGE, LAW, LOC, MONEY, NORP, ORDINAL, ORG, PERCENT, PERSON, PRODUCT, QUANTITY, TIME, WORK_OF_ART`.
- spaCy 4.0 still pre-release (`4.0.0.dev2` from April 2024 is the latest dev tag); not shippable.
- **Pydantic migration:** spaCy 3.8.7+ dropped Pydantic v1 dependency in favor of custom validation in `confection` + `thinc`. Means our project's Pydantic v2 is no longer in conflict with spaCy's deps tree — **win**.

**License compliance with our MIT project:**
- en_core_web_lg has been MIT since v2.1.0 (2019). v2.2.5 metadata explicitly says `license: MIT`. Hugging Face listing confirms MIT.
- Source corpus is OntoNotes 5 + WordNet 3.0 + Explosion vectors (OSCAR/Wikipedia/OpenSubtitles). OntoNotes corpus license restricts only the corpus itself, not the derived embeddings — already navigated by Explosion at distribution time. **Safe.**

**Recommendation:**
```toml
spacy = ">=3.8.10,<3.9"
# model installed via post-install:
# uv run python -m spacy download en_core_web_lg
# or pinned wheel:
# en_core_web_lg @ https://huggingface.co/spacy/en_core_web_lg/resolve/main/en_core_web_lg-any-py3-none-any.whl
```

The model is **not** a Python package on PyPI in the traditional sense; install via either `spacy download` or direct wheel pin. Story-entity-gate.md line 89 (`uv run python -c "import spacy; spacy.load('en_core_web_lg')"`) is correct.

---

### §3 — **Should we drop spaCy?** (evidence-based recommendation)

**Spec's question:** *"Real cost: spacy is huge (~750MB model) and dotnet/Python load time is non-trivial. Should we DROP spacy and use pure regex?"*

**Tally of what the entity gate must catch (architecture.md §4.7):**

| Entity type | Regex-only sufficient? | Why |
|---|---|---|
| IPv4 / IPv6 | YES | RFC-shaped, regex-stable |
| MD5 / SHA1 / SHA256 | YES | Fixed-length hex, regex-stable |
| Windows registry keys | YES | `HK(LM|CU|U|CR|CC)\\…` pattern |
| Windows paths | YES | `[A-Z]:\\…` |
| POSIX paths | MAYBE | `/(?:[^/\s]+/?)+` over-matches prose; spaCy adds zero help here |
| Account names | YES | `DOMAIN\\user` pattern |
| Mutex names | YES | `Global\\…` / `Local\\…` |
| Port numbers | YES (contextual regex) | `port \d{1,5}` |
| Emails | YES | RFC 5322 simplified regex |
| URLs | YES | `https?://…` |
| Process names (e.g., `svchost.exe`) | MAYBE | regex `\b[a-zA-Z0-9_.-]+\.exe\b` works for `.exe`/`.dll`; spaCy NER would tag these as `WORK_OF_ART`/`PRODUCT`, low signal |
| **Person names** (e.g., "Mr. Evil", "Bob") | **NO — only spaCy catches these** | Regex can't distinguish "Bob" from "log" |
| **Organization names** ("ETH", "Microsoft") | **NO — spaCy F1 on ORG = 0.79** | Regex can't disambiguate caps |
| **GPE** (countries, cities) | **NO — spaCy GPE F1 = 0.85** | Critical for "we traced the IP to Brazil" claims |

**Verdict: KEEP spaCy.** Here's why:

1. **The hallucination class spaCy catches is the one we most need to catch.** Models confabulate plausible-sounding ORG names ("Mandiant", "CrowdStrike", "Lazarus Group") more readily than IP addresses. The architectural floor must reject "the malware was attributed to Lazarus Group" if "Lazarus Group" never appears in a cited span. Regex cannot do this — only NER can identify "Lazarus Group" as an ORG entity worth checking against cited spans. **This is the highest-value capture in the entity gate.**

2. **Cost is real but bounded.** 789 MB model, 3s cold load — but lazy-loaded at module level (spec line 119 already does this), amortized across the entire investigate run. Docker layer caches the model after first pull. On SIFT 2026 the model fetches once per case-directory init.

3. **DFIR domain language explicitly demands ORG/PERSON tagging.** PRD §6 (epistemic-honesty metric) rewards refusing claims like "the threat actor APT29 was responsible" when nothing in the evidence attributes to APT29. APT names are caught by NER, not regex.

4. **Architecture commits in ADR-006.** Reading architecture §4.7 + ADR-006 (rationale for spaCy + regex over LLM-as-extractor) — switching to pure regex would invalidate the ADR and require an architecture re-review.

5. **Alternative considered: GLiNER / FlairNLP.** GLiNER is a 100M-param zero-shot NER model (~400MB, BERT-based) that beats spaCy F1 on niche labels. **Rejected:** GLiNER requires PyTorch + transformers (~2GB cumulative deps), making the install heavier than spaCy. Spike point: GLiNER is a worthy upgrade in a v2; not on the v1 critical path.

6. **Alternative considered: drop NER, raise regex specificity.** **Rejected:** the `PERSON`/`ORG`/`GPE` tags are not regex-modellable without an exhaustive vocabulary. We'd ship false negatives on every novel APT/threat-actor name — the exact class of claim our floor needs to police.

**Action: Keep spaCy. Document in ADR-006 (already done) that we accept the 789 MB cost.** Pin `en_core_web_lg==3.8.0` to lock the F1.

**Performance footnote:** If cold-load latency becomes a demo-day-killer, switch model to `en_core_web_md` (~50 MB, F1 ~0.84 — basically equivalent for our entity types) — single-line code change. Document this as v1.1 escape hatch in architecture.

---

### §4 — mistune `escape=False` security envelope (FIX-IT, P1)

**Spec note in story-report-pdf-export.md line 153:** *"`escape=False` is REQUIRED so the `<sup>` tags inside link text (from `VerifyLinkRenderer.expand_for_pdf`) pass through."*

**Reality of `escape=False`:**

- `escape=False` tells mistune **not to HTML-escape content of code blocks and inline-html spans**. It does NOT make mistune unsafe per se — it just delegates the escaping decision back to upstream renderers.
- **2026 CVE wave on mistune** (all in versions ≤3.2.0, all patched in 3.2.1):
  - **CVE-2026-44708** — math plugin renders `$...$` and `$$...$$` raw HTML, bypassing `escape=True`. Doesn't affect us (we don't use the math plugin).
  - **CVE-2026-44896** — figure directive `figclass`/`figwidth` rendered unescaped. Doesn't affect us (no figure directive).
  - **CVE-2026-44897** — heading ID attribute injection via crafted heading text. **AFFECTS US**: our 9-section template includes headings (`## Executive Summary` etc.) — but the content of these headings is hard-coded in `SECTION_HEADINGS` and never derived from user input. Safe in practice. Still — pin 3.2.1 to remove the surface.
  - **CVE-2026-44899** — image directive CSS injection unaffected by `escape=True`. Doesn't affect us (no image directive).
  - **CVE-2026-33441 / 33079** — DoS via `LINK_TITLE_RE` ReDoS on crafted markdown. **AFFECTS US** if the Markdown contains adversary-controlled link titles. Our findings are emitted by the agent (model-controlled), then verified by the entity gate + citation gate; an adversarial finding could in theory smuggle a DoS title. Pin 3.2.1 closes this.

**Threat model for SilentWitness:**
- The Markdown we render is **written by our own template + writer**, not by an external untrusted source.
- The only "untrusted" content path is verbatim cited spans from tool output (which can include adversary-controlled artifact contents).
- Those spans land inside `<pre><code>` blocks (story-report-writer enforces) — `escape=False` does NOT pass them through unescaped; they're in code-block context where mistune renders them as-is into `<pre>` tags. The `<` and `>` are still escaped inside code blocks.
- The architecturally-dangerous path would be if a cited span ended up in a Markdown link title (`[text](url "title")`) — that's the CVE-2026-33441 / 44897 surface. We don't generate Markdown links from cited spans; verify-links are injected as `<sup>` HTML tags by `VerifyLinkRenderer.expand_for_pdf`, which is upstream of mistune.

**Verdict:**
- `escape=False` is **acceptable** for our use case, given the locked input shape.
- **MUST pin mistune ≥3.2.1** to close the live CVEs.
- Add a code comment in `report/pdf.py` explaining the `escape=False` rationale + the upstream guardrails (template-controlled HTML; cited spans confined to code blocks; verify-link HTML emitted by trusted renderer).

**Action items for story-report-pdf-export.md:**
- Line 23: change `mistune.create_markdown(escape=False, plugins=["table", "url", "strikethrough"])` — keep as-is.
- Add to "Notes for coding agent" (line 153): *"mistune must be pinned ≥3.2.1; 3.2.0 and earlier carry 6 CVEs around HTML injection. `escape=False` is safe in our context because (a) the Markdown source is template-generated, (b) cited spans live inside `<pre><code>` blocks where they are rendered verbatim but the surrounding tags are not adversary-controlled, (c) verify-link `<sup>` tags are emitted by the trusted `VerifyLinkRenderer`, not parsed by mistune."*

**Recommendation:**
```toml
mistune = ">=3.2.1,<4"
```

---

### §5 — structlog: do we even need it? (KEEP-but-question)

**Spec assumption (story-audit-logger.md line 126):** *"`structlog` topic `JSONL bound logger` (the recommended pattern for our scope is direct `model_dump_json()` write, NOT structlog — but check current 24+ docs in case we benefit from structlog's contextvars binding for examiner threading)."*

**Reality:**
- structlog current = **25.5.0** (2025-10-27). Spec's `24+` is fine as a floor.
- structlog 25.x added Python 3.14 support and the `pad_event → pad_event_to` rename (deprecation, not break). No breaking API changes that affect our use.
- structlog is excellent for **app logging** (`logger.info(...)`) where the output is consumed by a structured log aggregator. We do not have that use case. Our audit log is a **strict-schema Pydantic model serialized to a single file per backend**, with no structlog formatters between us and the file.
- The spec itself acknowledges this on line 126: *"the recommended pattern for our scope is direct `model_dump_json()` write, NOT structlog."*

**Recommendation:**
- **REMOVE structlog from the spec'd deps** unless story-audit-logger's coding agent explicitly chooses it. Our audit path is: build `AuditEntry` Pydantic model → `entry.model_dump_json()` → `atomic_io.append_jsonl_line(path, line + "\n")` → done. structlog adds zero value here and one transitive dep + ~50 KB.
- If a future story (CLI debug logging? MCP server lifecycle telemetry?) wants structured app logging, **then** add structlog. Today it's dead weight.

**Action:**
- Remove `structlog` from the recommended `pyproject.toml` deps block (see §15 below).
- Update story-audit-logger.md line 126 hint: *"do NOT use structlog; the AuditEntry → model_dump_json + atomic-io append pattern is sufficient and removes one runtime dep."*

If retained anyway, pin: `structlog>=25.4,<26`.

---

### §6 — httpx (KEEP, low risk)

- Latest stable: **0.28.1** (2024-12-06; ~18 months stable).
- v1.0 in dev (`1.0.dev3` Sept 2025) but **not shipped**. Don't speculate on 1.0 API; pin 0.28.x.
- API surface we use: `httpx.Client(timeout=...)`, `client.post(...)`, `client.stream(...)`, `httpx.Timeout(...)`, `httpx.Limits(...)`. All stable since 0.25.
- For MCP HTTP transport (FastMCP transport client): the pattern `httpx.AsyncClient` + connection pool reuse is documented + battle-tested.
- **PoolTimeout caveat** (encode/httpx#2556): under heavy concurrent reuse of `AsyncClient`, the pool can deadlock; mitigation = lower `max_keepalive_connections` to `10` and recreate client per investigate run. **Probably not our problem** at hackathon scale (1 examiner, 1 case at a time), but document.

**Recommendation:**
```toml
httpx = ">=0.28,<0.29"
```

---

### §7 — hypothesis (KEEP)

- Current: **6.151.11** (2026-04-05). Spec's `6+` is correct but stale.
- Patterns we use (per story-audit-logger property tests): `@given(...)`, `strategies.lists(...)`, `strategies.sampled_from(...)`, `assume(...)`. All stable since 6.0.
- `HYPOTHESIS_PROFILE=ci` env var (story-audit-logger shell verification line 89): documented + stable.

**Recommendation:**
```toml
hypothesis = ">=6.140,<7"
```

---

### §8 — **uv version slip is a BLOCKER (P0)**

**Spec assumption (story-docker-baseline.md line 21):** *"`uv 0.5.11` install"*. Also CICD_SPEC §11.1 pin (line 113): *"Do NOT change the `uv` version (0.5.11 — pinned in CI matrix env)."*

**Reality:**
- uv current = **0.11.18** (2026-06-01).
- 17 minor versions stale.
- Breaking semantics changes between 0.5 → 0.11:
  - `uv venv` now requires `--clear` to delete existing venvs (previously silent overwrite).
  - Multiple `[[tool.uv.index]]` blocks with `default = true` now **error** at config time.
  - Unnamed explicit indexes now rejected.
  - Lockfile `exclude-newer` semantics changed (no longer auto-invalidates the lock).
  - `uv tool run` and `uv tool install` now respect `uv python pin --global`.
  - Alternative Python implementations (PyPy, GraalPy, Pyodide) now installed with implementation name (`pypy3.10`) not generic (`python3.10`).
  - Credential matching now errors on ambiguous matches.
  - Build-system upper bounds (`<0.11.0`) need to be re-checked.

**Why this matters for our spec:**
- Dependent stories assume modern uv behavior (lockfile semantics, default index handling). Pinning 0.5.11 means coding agents who copy stock 2026 install scripts will hit incompatible defaults.
- The Dockerfile install pattern (`pip install uv==0.5.11` or `RUN curl -LsSf https://astral.sh/uv/install.sh | sh`) needs to track current astral installer.

**Recommendation:**
- Bump pin: `uv==0.11.18` in Dockerfile.
- pyproject.toml has no need for a `requires-uv` field (uv doesn't enforce that), but document in `CONTRIBUTING.md` (or CICD_SPEC §11.1): *"uv 0.11+ required. Lockfile semantics, default-index handling, and `uv venv --clear` requirement assume ≥0.11."*
- Re-run `uv sync --frozen` semantics on current version to confirm `uv.lock` deterministic across machines. Per uv docs (https://docs.astral.sh/uv/concepts/projects/sync/) `--frozen` does NOT regenerate the lock; it errors if the lock is stale. This is what we want for CI.

**Action items:**
- CICD_SPEC §11.1: change `uv 0.5.11` → `uv 0.11.18`.
- story-docker-baseline.md line 21: same.
- story-cli-install-claude-code (if it exists) install.sh: same.

---

### §9 — pytest (KEEP, floor bump)

- Current: **9.0.3** (2026-04-07).
- 9.0.0 (Nov 2025) added native TOML config support; minor breaking changes around `pytest.ini` → `pyproject.toml` defaults. Our spec is already TOML-first (CICD_SPEC), so this is a **WIN**.
- The 9.0.0 terminal-progress feature was disabled by default in 9.0.1 due to terminal-emulator compatibility issues — non-impact for us.

**Recommendation:**
```toml
pytest = ">=9.0,<10"
```

---

### §10 — rich (KEEP, verified working)

- Current: **15.0.0** (2026-04-12). Spec doesn't pin rich directly — it's a transitive of Typer.
- 15.0.0 explicitly added **nested Live object support** ("Live objects may now be nested. Previously a progress bar inside another progress context would fail") — this directly enables the story-cli-investigate HUD pattern where a top-level Live wraps a Progress wraps a Table.
- Dropped Python 3.8 support. We're on 3.12 — safe.
- `typing_extensions` removed from runtime deps. Smaller install.

**Recommendation (explicit pin to lock the nested-Live behavior we depend on):**
```toml
rich = ">=14.1,<16"
```

---

### §11 — WeasyPrint native dep matrix on python:3.12-slim (FIX-IT)

**Spec's Dockerfile dep list (story-docker-baseline.md line 21):** *"WeasyPrint native deps (libcairo2 / libpango / libgdk-pixbuf / libffi8 / shared-mime-info)"*

**Reality (verified from WeasyPrint stable docs + current Dockerfile examples):**

For `python:3.12-slim-bookworm` (Debian 12 base — the explicit bookworm tag we should pin):

```bash
apt-get install -y --no-install-recommends \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libharfbuzz0b \
  libharfbuzz-subset0 \
  libcairo2 \
  libgdk-pixbuf-2.0-0 \
  libffi8 \
  shared-mime-info \
  fonts-source-serif-pro \
  fonts-source-code-pro
```

**Findings:**
1. Spec's list **omits `libharfbuzz-subset0`** — required by WeasyPrint 68+ for subsetting embedded fonts. Without it, font embedding silently degrades.
2. Spec's list **omits `libpangoft2-1.0-0`** — required for PangoFT2 integration which WeasyPrint uses for font shaping on Linux.
3. Spec's list **omits font packages**. `fonts-source-serif-pro` is referenced in story-report-pdf-export.md line 155 but never added to the Dockerfile dep list. JetBrains Mono is *not* in Debian apt; either bundle the .ttf or accept `monospace` fallback.
4. **Base image tag must be explicit:** `python:3.12-slim` floats to whatever Debian release is current (trixie since Aug 2025). Pin `python:3.12-slim-bookworm` to keep apt names stable. Alternative: `python:3.12-slim-trixie` (Debian 13) — but then `libffi8` becomes `libffi8` still (verified). Both work; pick bookworm for max stability through hackathon.

**Action items for story-docker-baseline.md:**
- Pin base image to `python:3.12-slim-bookworm`.
- Expand apt-get list to include `libharfbuzz-subset0`, `libpangoft2-1.0-0`, `fonts-source-serif-pro`, `fonts-source-code-pro`.
- Document JetBrains Mono fallback in README.

**Issue #2782 (fontconfig 2.18.0 macOS font matching) note:** Linux containers run their own fontconfig, not the host's. Docker users on macOS Apple Silicon get a clean linux fontconfig inside the container — **not affected**. Document for mac dev users running WeasyPrint outside Docker.

---

### §12 — pypdf (KEEP)

- Current: **6.12.2** (2026-05-26).
- Pure Python, Python ≥3.9, production-stable.
- `PdfReader(...).pages[i].extract_text()` — the documented + stable API, matches story-report-pdf-export.md test pattern verbatim.
- Recent improvements (6.10.x → 6.12.x): faster `_decode_png_prediction`, better loop control in text extraction.
- No CVEs in the 6.x line (latest CVE was on pypdf 3.x, 2024-04).

**Recommendation:**
```toml
pypdf = ">=6.10,<7"
```

Story-report-pdf-export.md line 175 Context7 hint: keep as-is.

---

### §13 — matplotlib (KEEP, spec correct)

- Current: **3.10.9** (2026-04-24).
- Spec's minor-pin (`3.10.x`) is correct discipline — PNG byte-stability for the demo bar chart requires locking the minor.
- `Agg` backend pattern: `matplotlib.use('Agg')` before importing pyplot — stable for years, documented in story-delta-report.md line 156 correctly.
- Defer-import pattern (`import matplotlib.pyplot` inside `render_bar_chart_png` to avoid 600ms cold-load) — correct.
- PNG metadata determinism via `metadata={"Software": ...}` + `pil_kwargs={"optimize": True}` — correct.

**Recommendation:**
```toml
matplotlib = ">=3.10,<3.11"
```

Spec is correct. No action.

---

### §14 — **pytsk3 + pefile + python-evtx + regipy (BLOCKER on regipy + python-evtx — write API missing)**

**Spec claims (story-case-trapdoor-synthesis.md):**
- `synth_logclear` uses `python-evtx` to **build** a synthetic EVTX file (line 27).
- `synth_registry_injection` uses `regipy` to **write** a registry hive (line 29).
- `synth_runkey_persistence` **appends** a Run-key entry to the same hive (line 30).

**Reality:**

| Library | Current | Read | Write | License | Verdict |
|---|---|---|---|---|---|
| pytsk3 | 20260520 | ✓ | partial (low-level libtsk write API exists but is fragile) | BSD-style (libtsk: CDDL+GPL) | OK with caveat |
| pefile | 2024.8.26 | ✓ | ✓ (`PE.write()` documented) | MIT | OK |
| python-evtx | 0.8.1 (2025-05-02) | ✓ | **✗ READ-ONLY** | Apache 2.0 | **BLOCKER** |
| regipy | 6.2.1 (2026-01-22) | ✓ | **✗ READ-ONLY** | MIT | **BLOCKER** |

**Two of the five `synth_*` helpers cannot be implemented as spec'd:**
- `synth_logclear` needs to **emit** an EVTX file with EID 1102 — python-evtx provides no write API. Spec notes (line 188): *"`python-evtx` EID 1102 has a specific binary XML schema — fetch a reference EVTX file with a real EID 1102 (from a clean Windows test VM) and use it as a template; do not hand-construct the binary XML."* This works around the read-only constraint by templating from a reference file. **OK only if we ship a reference EVTX in the repo as a fixture.**
- `synth_registry_injection` + `synth_runkey_persistence` need to **write** registry hive values — regipy provides no write API. Spec notes (line 186): *"regipy is read-mostly; the write API is limited — may need `python-registry` as fallback for hive writing."* But `python-registry` (Willi Ballenthin's hive parser) is **also primarily read-only**.

**Real options for registry write:**
1. **Ship a template NTUSER.DAT** from a clean Windows VM as a binary fixture. Read it with regipy, but write modifications using **`hivexml` / `hivex`** (libhivex from libguestfs). Adds C dep `libhivex0` + `python3-hivex` apt package. Linux-only; would work in our container.
2. **Use `winreg`** — Windows-only stdlib module. Not viable cross-platform.
3. **Use `Registry::Hive` (Perl)** — out of scope.
4. **Generate the hive offline** from a Windows VM (one-time) and check the seeded binary into the repo as a fixture (`harness/case-trapdoor/templates/NTUSER_TEMPLATE.dat`). Then `synth_*` patches it in-place by **byte-offset** for the specific keys we know are there. Brittle, but deterministic per seed.

**Story-case-trapdoor-synthesis is OPTIONAL (Epic 15 cuttable per epics.md §1 + PRD §9 "time-permitting").** This means we can:
- **Ship the story as-is, mark `synth_logclear` + `synth_registry_injection` + `synth_runkey_persistence` as "requires `hivex` + template fixture; skipped if not available"**, document the constraint in `harness/case-trapdoor/README.md`.
- **OR cut the story entirely** and demo on the three real datasets (Nitroba, ZeroAccess, Stuxnet) where Epic 14 already measures Δ.

**Recommendation:**
- **CUT** story-case-trapdoor-synthesis from v1 critical path. Promote to v2 stretch.
- If retained: rewrite the file modification map to document the template-fixture approach + `hivex` system dep. Add an Epic 15 NOTE in epics.md that this is now contingent on libhivex availability and a checked-in template hive.

**Pins (if retained):**
```toml
[project.optional-dependencies.case_trapdoor]
pytsk3 = ">=20240115"
pefile = ">=2024.8.26"
python-evtx = ">=0.8.1"
regipy = ">=6.2,<7"
# + system: libhivex0 + python3-hivex (apt) for registry write
```

**SIFT 2026 / Ubuntu 24.04 install path:**
- All four packages have wheels on PyPI for CPython 3.12 x86_64-manylinux. **No build-from-source required.**
- pytsk3 requires libtsk runtime on Linux — `apt install libtsk19` (no `-dev` needed for the wheel path).
- python-evtx + regipy + pefile are pure Python.

---

## Cross-cutting findings

### F-1: `python:3.12-slim` floating tag is a CI footgun
Pin `python:3.12-slim-bookworm` (Debian 12) explicitly. Floating `python:3.12-slim` will flip to trixie (Debian 13) or forky (Debian 14) over the hackathon window and break apt package names + ldconfig paths.

### F-2: We've been carrying obsolete pins through multiple stories
WeasyPrint 60.x, uv 0.5.11, structlog 24+, pytest 8+. None of these floors are wrong — they're just **stale by 12-18 months**. Bumping floors closes ~10 known CVEs in transitive deps. Do this once, store the pinned `pyproject.toml` recommendation below.

### F-3: No story should pin spaCy + en_core_web_lg version independently
spaCy major releases ship with model-compatibility breaks. Pin model to spaCy minor: `spacy>=3.8.10,<3.9` + `en_core_web_lg==3.8.0`.

### F-4: Coverage policy on `report/pdf.py` is correct
CICD_SPEC §8.1 excludes pdf.py from coverage (WeasyPrint render shim, covered by integration smoke). Verified against story-report-pdf-export.md acceptance criteria — the integration tests do exercise the WeasyPrint path. **Keep the exclusion.**

### F-5: mistune CVE wave forces an explicit lower-bound pin (not floor-only)
"mistune>=3" is unsafe (lets 3.0.x, 3.1.x in, all vulnerable). Pin `>=3.2.1,<4` — this is non-negotiable.

---

## Recommended `pyproject.toml` deps block (consolidated)

```toml
[project]
name = "silentwitness"
requires-python = ">=3.12,<3.13"

dependencies = [
    # PDF render
    "weasyprint>=68.1,<70.0",
    "mistune>=3.2.1,<4",         # 3.2.1 closes 6 CVEs (XSS + DoS)
    "pyyaml>=6.0,<7",
    "pypdf>=6.10,<7",            # test side; dev-only if you prefer

    # NER + entity gate
    "spacy>=3.8.10,<3.9",
    # en_core_web_lg installed post-install via `python -m spacy download en_core_web_lg`
    # or pinned wheel; pin spaCy minor to lock model compat

    # CLI
    "typer>=0.20,<0.27",
    "rich>=14.1,<16",            # 15.0 added nested Live which we depend on

    # Validation
    "pydantic>=2.10,<3",         # (verified separately in 01-pydantic-ai-verification.md)

    # HTTP
    "httpx>=0.28,<0.29",
]

[dependency-groups]
dev = [
    "pytest>=9.0,<10",
    "pytest-cov>=6.0,<7",
    "hypothesis>=6.140,<7",
    "mypy>=1.13,<2",
    "ruff>=0.8,<0.9",
    "coverage>=7.6,<8",
]

# Optional — only needed if Epic 15 (case-trapdoor) ships
[project.optional-dependencies]
case_trapdoor = [
    "pytsk3>=20240115",
    "pefile>=2024.8.26",
    "python-evtx>=0.8.1",        # READ-ONLY; spec assumes write — must rewrite story
    "regipy>=6.2,<7",            # READ-ONLY; spec assumes write — must rewrite story or cut
]

# REMOVED from spec'd deps:
# - structlog: dead weight for our use case (use AuditEntry.model_dump_json directly).
#   Re-add if a future story wants app-level structured logging.

[tool.uv]
# uv 0.11.18 required (see audit §8 for breaking changes vs 0.5.11)
```

**Dockerfile pin** (story-docker-baseline.md):
```dockerfile
FROM python:3.12-slim-bookworm AS build

# uv 0.11.18 (was 0.5.11 — 17 minor versions stale, breaking semantics changes)
RUN curl -LsSf https://astral.sh/uv/0.11.18/install.sh | sh

# WeasyPrint native deps for Debian Bookworm
# spec was missing libharfbuzz-subset0 + libpangoft2-1.0-0 + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-source-serif-pro \
    fonts-source-code-pro \
    libtsk19 \
    && rm -rf /var/lib/apt/lists/*
```

---

## Spec-file action checklist

| File | Line | Change |
|---|---|---|
| `docs/stories/story-report-pdf-export.md` | 152 | `weasyprint>=60,<62` → `weasyprint>=68.1,<70.0` |
| `docs/stories/story-report-pdf-export.md` | 153 | Add: *"mistune must be ≥3.2.1; 3.2.0 ships with 6 unpatched CVEs around HTML injection."* |
| `docs/stories/story-report-pdf-export.md` | 173 | Note v68+ deprecates `default_url_fetcher` — not used by us; `base_url` pattern stable. |
| `docs/stories/story-docker-baseline.md` | 21 | `uv 0.5.11` → `uv 0.11.18`; pin base image to `python:3.12-slim-bookworm`; expand apt list. |
| `docs/CICD_SPEC.md` | §11.1 | Same as above. |
| `docs/stories/story-audit-logger.md` | 126 | Update Context7 hint: *"do NOT add structlog as a runtime dep; use `AuditEntry.model_dump_json()` + `atomic_io.append_jsonl_line` directly."* |
| `docs/stories/story-entity-gate.md` | 119 | Tighten size: 789 MB download / 741 MB install (was "750 MB"). |
| `docs/stories/story-entity-gate.md` | 142 | Add: *"spaCy 3.8.10+ drops Pydantic v1 dep (uses confection/thinc); no conflict with our Pydantic v2."* |
| `docs/stories/story-case-trapdoor-synthesis.md` | (entire) | **Rewrite** to document regipy + python-evtx read-only constraint; introduce template-fixture approach OR cut from v1. |
| `docs/epics.md` | Epic 15 | Note Epic 15 contingent on `libhivex0` + checked-in template hive fixture. |
| `docs/architecture.md` | §11 (runtime deps) | Sync with consolidated `pyproject.toml` block above. |

---

## Sources

**WeasyPrint:**
- [PyPI weasyprint](https://pypi.org/project/weasyprint/)
- [WeasyPrint Stable Docs — Changelog](https://doc.courtbouillon.org/weasyprint/stable/changelog.html)
- [WeasyPrint Stable Docs — First Steps (install deps)](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)
- [WeasyPrint Stable Docs — API Reference (PDF anchors)](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html)
- [Issue #2782 — fontconfig 2.18.0](https://github.com/Kozea/WeasyPrint/issues/2782)
- [Issue #2655 — anchor with `(`](https://github.com/Kozea/WeasyPrint/issues/2655)

**spaCy + model:**
- [PyPI spacy](https://pypi.org/project/spacy/)
- [spaCy 3.8.x Releases](https://github.com/explosion/spaCy/releases)
- [Hugging Face spacy/en_core_web_lg (license + F1 + entity types)](https://huggingface.co/spacy/en_core_web_lg)
- [spaCy What's New v3.7](https://spacy.io/usage/v3-7)
- [Pydantic v1 drop discussion #13196](https://github.com/explosion/spaCy/issues/13196)

**mistune:**
- [PyPI mistune](https://pypi.org/project/mistune/)
- [Mistune 3.2.1 Changelog](https://mistune.lepture.com/en/latest/changes.html)
- [CVE-2026-44708 (math plugin XSS)](https://advisories.gitlab.com/pypi/mistune/CVE-2026-44708/)
- [CVE-2026-44896 (figure directive XSS)](https://advisories.gitlab.com/pypi/mistune/CVE-2026-44896/)
- [CVE-2026-44897 (heading ID injection)](https://advisories.gitlab.com/pypi/mistune/CVE-2026-44897/)
- [CVE-2026-33441 (DoS)](https://advisories.gitlab.com/pypi/mistune/CVE-2026-33441/)
- [CVE-2026-33079 (ReDoS LINK_TITLE_RE)](https://advisories.gitlab.com/pypi/mistune/CVE-2026-33079/)

**structlog:**
- [PyPI structlog](https://pypi.org/project/structlog/)
- [structlog 25.5.0 docs](https://www.structlog.org/)

**Typer + Rich:**
- [PyPI typer](https://pypi.org/project/typer/)
- [Typer Release Notes](https://typer.tiangolo.com/release-notes/)
- [PyPI rich (15.0.0)](https://pypi.org/project/rich/)
- [Rich Live Display docs](https://rich.readthedocs.io/en/latest/live.html)

**httpx:**
- [PyPI httpx](https://pypi.org/project/httpx/)
- [HTTPX Timeouts docs](https://www.python-httpx.org/advanced/timeouts/)
- [HTTPX Resource Limits docs](https://www.python-httpx.org/advanced/resource-limits/)

**uv:**
- [PyPI uv (0.11.18)](https://pypi.org/project/uv/)
- [uv GitHub Releases](https://github.com/astral-sh/uv/releases)
- [uv Changelog (breaking changes 0.5→0.11)](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- [uv concepts: projects/sync (--frozen semantics)](https://docs.astral.sh/uv/concepts/projects/sync/)

**pytest:**
- [PyPI pytest (9.0.3)](https://pypi.org/project/pytest/)

**hypothesis:**
- [PyPI hypothesis (6.151.11)](https://pypi.org/project/hypothesis/)

**pypdf:**
- [PyPI pypdf (6.12.2)](https://pypi.org/project/pypdf/)
- [pypdf 6.12.2 install docs](https://pypdf.readthedocs.io/en/stable/user/installation.html)

**matplotlib:**
- [PyPI matplotlib](https://pypi.org/project/matplotlib/)
- [Matplotlib 3.10.9 release notes](https://matplotlib.org/stable/users/release_notes.html)

**Case-trapdoor stack:**
- [PyPI pytsk3 (20260520)](https://pypi.org/project/pytsk3/)
- [PyPI pefile (2024.8.26)](https://pypi.org/project/pefile/)
- [PyPI python-evtx (0.8.1)](https://pypi.org/project/python-evtx/)
- [PyPI regipy (6.2.1)](https://pypi.org/project/regipy/)
- [williballenthin/python-evtx GitHub](https://github.com/williballenthin/python-evtx)
