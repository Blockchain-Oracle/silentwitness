# Story — hayabusa_csv_timeline tool wrapper (Hayabusa)

**ID:** story-hayabusa-timeline
**Epic:** Epic 7 — Tool wrappers: log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata)
**Depends on:** story-parse-evtx (skeleton: `_run_dotnet_log_tool`, `_normalize_and_store`, `_LogResult`, `_log_common.py`)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or any MCP client)
**I want to** wrap Hayabusa's `csv-timeline` subcommand as a typed MCP tool `hayabusa_csv_timeline`
**So that** I receive a typed list of `HayabusaHit` rows with Sigma-rule detections (including `MitreTactics` + `MitreTags` extracted as first-class fields) over an EVTX corpus — load-bearing for the demo's narrative drafting (the MITRE TTPs map directly into the report's Findings section and the critic's CHALLENGE corroboration at 4:00–4:30) (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy).

---

## File modification map

- `src/silentwitness_mcp/tools/log.py` — UPDATE — add `hayabusa_csv_timeline(input: HayabusaInput) -> ToolResponse[HayabusaOutput]` wrapper (~120 LOC delta) reusing `_run_dotnet_log_tool` is **not** appropriate here (Hayabusa is a native Rust binary, not a dotnet DLL) — instead reuse the generic subprocess + normalize + audit pattern via a parallel helper `_run_native_log_tool(bin_path: Path, argv: list[str], timeout_s: float) -> _LogResult` added to `_log_common.py` in this story (same `_LogResult` return shape so the audit-blob writer is shared). Pydantic models: `HayabusaInput(evtx_dir: Path, csv_out: Path, min_level: Literal["informational", "low", "medium", "high", "critical"] | None = None, include_tags: list[str] | None = None, profile: Literal["minimal", "standard", "verbose", "super-verbose", "all-field-info"] = "super-verbose")`, `HayabusaHit(Timestamp: datetime, RuleTitle: str, Level: str, Computer: str, Channel: str, EventID: int, RecordID: int, MitreTags: list[str], MitreTactics: list[str], RuleAuthor: str | None, Detection: str, RuleFile: str, EvtxFile: str)`, `HayabusaOutput(hits: list[HayabusaHit], row_count: int, truncated: bool, rules_loaded: int | None)`.
- `src/silentwitness_mcp/tools/_log_common.py` — UPDATE — add `HAYABUSA_BIN = Path("/opt/hayabusa/hayabusa")`, `HAYABUSA_RULES_DIR = Path("/opt/hayabusa-rules")`, `_run_native_log_tool(...)` async helper (signature mirrors `_run_dotnet_log_tool` so the audit writer downstream is identical), extend `LogFailureReason` enum with `HAYABUSA_NOT_INSTALLED` and `HAYABUSA_RULES_MISSING`, append `_LOG_CAVEATS["hayabusa_csv_timeline"]` entries verbatim from `context/domain/06` §7.1 Limitations.
- `src/silentwitness_mcp/server.py` — UPDATE — register `hayabusa_csv_timeline` with the FastMCP `Server`.
- `install.sh` — UPDATE — add `install_hayabusa()` step that `curl -L`s the Hayabusa release tarball from `https://github.com/Yamato-Security/hayabusa/releases/download/v3.9.0/hayabusa-3.9.0-lin-x64-gnu.zip` (Hayabusa pinned to **v3.9.0** — verified SHA256 in docs/.audit/06-sift-and-datasets-verification.md), extracts to `/opt/hayabusa/`, and `git clone`s the rules corpus from `https://github.com/Yamato-Security/hayabusa-rules` to `/opt/hayabusa-rules/` per `context/.raw-design-research/03` §"Tools our install script MUST add" line 271 + line 279. Pin a SHA256 for the release zip in the script (release-version pinned, NEVER `latest`) so reproducibility holds.
- `tests/fixtures/log/hayabusa_sample.csv` — NEW — small CSV (≤12 rows) mirroring real Hayabusa `super-verbose` profile output columns (PowerShell EncodedCommand T1059.001 hit + Sysmon CreateRemoteThread T1055 hit + Security 1102 audit-log-cleared T1070.001 hit).
- `tests/unit/tools/test_log_hayabusa.py` — NEW — ≥6 behavioural test cases: (a) valid Hayabusa CSV parses into `HayabusaOutput` with `MitreTags` and `MitreTactics` split from comma-separated columns into `list[str]`, (b) `min_level="high"` argument passes `--min-level high` correctly, (c) Hayabusa not installed at `/opt/hayabusa/hayabusa` returns `success=False` reason `HAYABUSA_NOT_INSTALLED` advisory pointing the agent at `install.sh`, (d) rules dir missing at `/opt/hayabusa-rules/` returns `success=False` reason `HAYABUSA_RULES_MISSING`, (e) Hayabusa exits non-zero (e.g., malformed EVTX in corpus) returns `success=False` reason `TOOL_FAILED`, (f) unregistered evidence directory returns `success=False` reason `EVIDENCE_NOT_REGISTERED`. Subprocess mocked via `monkeypatch` on `asyncio.create_subprocess_exec`.
- `tests/integration/tools/test_log_hayabusa_integration.py` — NEW — single e2e test invoking real `/opt/hayabusa/hayabusa csv-timeline -d <evtx_fixture_dir> -o <out> -p super-verbose` (skipped via `pytest.mark.skipif(not Path('/opt/hayabusa/hayabusa').exists())`).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered EVTX directory at /evidence/case-001/evtx/
And   the directory is registered in cases/case-001/evidence.json (each *.evtx file individually SHA256-pinned)
And   /opt/hayabusa/hayabusa exists and is executable
And   /opt/hayabusa-rules/ exists with ≥1 *.yml rule file
And   /evidence/ is mounted ro,noexec,nosuid
When  the MCP tool hayabusa_csv_timeline is called with HayabusaInput(evtx_dir=Path("/evidence/case-001/evtx/"), csv_out=Path("/tmp/hayabusa_out.csv"), profile="super-verbose")
Then  the response is ResponseEnvelope with success=True
And   data is a HayabusaOutput containing a list[HayabusaHit]
And   each HayabusaHit has typed fields: Timestamp: datetime (UTC), RuleTitle: str, Level: str (one of informational/low/medium/high/critical), Computer: str, Channel: str, EventID: int, RecordID: int, MitreTags: list[str], MitreTactics: list[str], RuleAuthor: str | None, Detection: str, RuleFile: str, EvtxFile: str
And   MitreTags is the parsed list from the comma-separated MitreTags column (e.g., ["T1059.001", "T1027"])
And   MitreTactics is the parsed list from the comma-separated MitreTactics column (e.g., ["execution", "defense_evasion"])
And   data_provenance.cmd_argv == ["/opt/hayabusa/hayabusa", "csv-timeline", "-d", "/evidence/case-001/evtx/", "-o", "/tmp/hayabusa_out.csv", "-p", "super-verbose", "--quiet", "--no-color", "--UTC"]
And   data_provenance.stdout_path points to cases/case-001/audit/blobs/<audit_id>.txt holding the normalized CSV bytes
And   data_provenance.result_sha256 is a 64-hex SHA256 of the normalized CSV
And   one JSONL line is appended to cases/case-001/audit/log.jsonl
And   caveats includes "Hayabusa output is detection-centric — there is no 'show all 4624 events' mode; use parse_evtx for raw event enumeration"
And   caveats includes "Hayabusa Sigma rule coverage reflects upstream — rules for very recent threats may lag; some Sigma correlation features (multi-event sequences) are partially implemented and may not fire"
And   caveats includes "Channel column may differ on non-English Windows (Windows localizes channel names in some metadata)"
And   corroboration includes a hint pointing at chainsaw_hunt for cross-engine Sigma corroboration (different mappings → different blind spots)

Given /opt/hayabusa/hayabusa does NOT exist on this host
When  hayabusa_csv_timeline is called
Then  the response is ResponseEnvelope with success=False reason="HAYABUSA_NOT_INSTALLED"
And   advisories[0] contains "Hayabusa is NOT pre-installed on SIFT 2026 — run install.sh to add it (see context/.raw-design-research/03 §'Tools our install script MUST add')"
And   no subprocess is spawned

Given /opt/hayabusa-rules/ does not exist OR contains no *.yml files
When  hayabusa_csv_timeline is called
Then  the response is ResponseEnvelope with success=False reason="HAYABUSA_RULES_MISSING"
And   advisories[0] points the agent at "install.sh which runs `git clone https://github.com/Yamato-Security/hayabusa-rules /opt/hayabusa-rules`"

Given HayabusaInput.min_level == "high"
When  hayabusa_csv_timeline is called
Then  data_provenance.cmd_argv includes "--min-level" followed by "high"
And   every HayabusaHit in the output has Level in {"high", "critical"}

Given HayabusaInput.include_tags == ["PowerShell", "Sysmon"]
When  hayabusa_csv_timeline is called
Then  data_provenance.cmd_argv includes "--include-tag" followed by "PowerShell,Sysmon"

Given the evtx_dir is not registered in cases/<case_id>/evidence.json
When  hayabusa_csv_timeline is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no Hayabusa subprocess is spawned

Given Hayabusa exits with a non-zero return code (e.g., a corrupt EVTX in the corpus)
When  hayabusa_csv_timeline is called
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL line records exit_code != 0 and elapsed_ms

Given Hayabusa exceeds the 600s timeout (large EVTX corpus)
When  hayabusa_csv_timeline is called
Then  the subprocess is terminated (SIGKILL after SIGTERM grace)
And   the response is ResponseEnvelope with success=False reason="TOOL_TIMEOUT"
```

---

## Shell verification

```bash
# Unit tests pass with ≥6 behavioural cases
uv run pytest tests/unit/tools/test_log_hayabusa.py -v

# Integration test skipped on non-SIFT runners
uv run pytest tests/integration/tools/test_log_hayabusa_integration.py -v

# Lint + format + strict types
uv run ruff check src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
uv run ruff format --check src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
uv run mypy --strict src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py

# File-size guard — aggregate cap across 3 log tools ≤400
wc -l src/silentwitness_mcp/tools/log.py | awk '{ if ($1 > 400) exit 1 }'

# Coverage floor for tools/log.py per CICD_SPEC §8.1 (85% target)
uv run coverage run -m pytest tests/unit/tools/test_log_hayabusa.py tests/unit/tools/test_log_parse_evtx.py
uv run coverage report --include="src/silentwitness_mcp/tools/log.py,src/silentwitness_mcp/tools/_log_common.py" --fail-under=85

# install.sh provisions Hayabusa to the documented path
grep -E "hayabusa" install.sh | grep -E "/opt/hayabusa/"
# Must output at least 1 line referencing the install path

# §13 banned patterns: no shell=True, no mock/fake/dummy in src/
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated|shell=True)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **Hayabusa is NOT pre-installed on SIFT 2026.** Verified `context/.raw-design-research/03` §Network forensics line 167 ("Hayabusa **NOT installed** (no `.sls`) — Valhuntir installs it themselves; SIFT base does not ship it") + §"Tools our install script MUST add" line 271 ("**Hayabusa** — `curl -L https://github.com/Yamato-Security/hayabusa/releases/latest/download/hayabusa-<ver>-lin-x64-gnu.zip` → `/opt/hayabusa/`") + line 279 ("**Hayabusa rules + Sigma rules** — git clone to `/opt/<rules>/`"). The wrapper MUST check `/opt/hayabusa/hayabusa` and `/opt/hayabusa-rules/` existence as the first action after evidence-registry checks and fail with structured `HAYABUSA_NOT_INSTALLED` / `HAYABUSA_RULES_MISSING` advisories pointing the agent at `install.sh`. This is a structural defense against the model running `apt install hayabusa` (which would fail) or fabricating a Hayabusa output.
- **install.sh delta** (per architecture §3 line 270 + Epic 1 + `context/.raw-design-research/03` §"Tools our install script MUST add"). The install script must:
  1. `curl -L` the Hayabusa **v3.9.0** release zip (version-pinned, SHA256-verified per docs/.audit/06-sift-and-datasets-verification.md) from `https://github.com/Yamato-Security/hayabusa/releases/download/v3.9.0/hayabusa-3.9.0-lin-x64-gnu.zip` to `/tmp/`, unzip to `/opt/hayabusa/`, rename the inner binary to `/opt/hayabusa/hayabusa` (Hayabusa releases use `hayabusa-3.9.0-lin-x64-gnu/hayabusa` directory shape — flatten it).
  2. `chmod +x /opt/hayabusa/hayabusa`.
  3. `git clone https://github.com/Yamato-Security/hayabusa-rules /opt/hayabusa-rules` (pin to a tag/SHA — do NOT clone `HEAD`; reproducibility per architecture §6 line 497).
  4. Verify the binary runs: `/opt/hayabusa/hayabusa --version` exits 0.
- **Hayabusa invocation pattern** (per `context/domain/06` §7.1 lines 1620–1636). Primary mode is `csv-timeline -d <evtx_dir> -o <out.csv>`. Force these flags in every invocation: `--quiet` (suppress banner so the normalizer has less to strip), `--no-color` (for piping; ensures clean CSV), `--UTC` (force UTC timestamps for cross-tool correlation), `-p <profile>` (default `super-verbose` — this is the profile that includes `MitreTags` and `MitreTactics` columns, which the demo's narrative drafting depends on per Strategy §wedge). When `min_level` is set, append `--min-level <level>`. When `include_tags` is set, append `--include-tag <comma-joined>` (Hayabusa expects comma-joined, NOT repeated `--include-tag` flags — verified `context/domain/06` §7.1 line 1711). Build `cmd_argv` deterministic for the audit log.
- **CSV column mapping** (per `context/domain/06` §7.1 line 1638 — `super-verbose` profile columns). Headers: `Timestamp`, `RuleTitle`, `Level`, `Computer`, `Channel`, `EventID`, `RecordID`, `Details`, `MitreTactics`, `MitreTags`, `OtherTags`, `RuleFile`, `EvtxFile`. `MitreTactics` and `MitreTags` columns are comma-joined strings — split into `list[str]` in the Pydantic validator. Empty string → `[]`. `Timestamp` is UTC ISO-8601 (because we forced `--UTC`) — parse to timezone-aware `datetime`. `Details` maps to `Detection` field in the Pydantic model (renamed for Python convention). `RuleAuthor` is extracted from the rule YAML at row-construction time when available; surface as `None` if absent from the Hayabusa output.
- **MITRE ATT&CK extraction is load-bearing.** Per `context/domain/06` §7.1 line 1715 ("Hayabusa output includes these in dedicated `MitreTactics` and `MitreTags` columns when the profile contains them"). The MITRE tags drive the narrative-drafting tool (`record_narrative`) downstream — without `MitreTags: list[str]` typed on the envelope, the narrative tool falls back to generic TTP labels and the entity gate cannot corroborate the ATT&CK references in the cited spans. Default profile MUST be `super-verbose` for this reason.
- **Subprocess helper.** Add `_run_native_log_tool(bin_path: Path, argv: list[str], timeout_s: float = 600.0) -> _LogResult` to `_log_common.py`. Same shape as `_run_dotnet_log_tool` from story-parse-evtx — async `create_subprocess_exec`, stdout+stderr capture, timeout with SIGTERM→5s→SIGKILL escalation, returns `_LogResult` with `exit_code`, `stdout_normalized`, `stderr`, `elapsed_ms`, `audit_id`, `stdout_path`, `result_sha256`. The audit-blob writer `_normalize_and_store` from story-parse-evtx is reused unchanged.
- **Evidence-registry semantics for directories.** Hayabusa's `-d <dir>` argument operates on every `*.evtx` under the directory. The evidence-registry pattern from story-evidence-registry registers individual files; for `evtx_dir`, the wrapper enumerates `*.evtx` files in the directory and calls `evidence_registry.assert_registered` for each. If ANY file is unregistered, fail closed with `EVIDENCE_NOT_REGISTERED` and the offending path list in advisories. This is the structural defense against an attacker dropping a fabricated EVTX into the evidence dir mid-case.
- **Caveats — verbatim discipline.** Source from `context/domain/06` §7.1 (Limitations + Gotchas). The exact strings to include in `_LOG_CAVEATS["hayabusa_csv_timeline"]`:
  - `"Hayabusa output is detection-centric — there is no 'show all 4624 events' mode; use parse_evtx for raw event enumeration"`
  - `"Hayabusa Sigma rule coverage reflects upstream — rules for very recent threats may lag; some Sigma correlation features (multi-event sequences) are partially implemented and may not fire"`
  - `"Channel column may differ on non-English Windows (Windows localizes channel names in some metadata)"`
  - `"Hayabusa cannot read XML or JSON-dumped events — EVTX format only"`
  Caveats appear in the report's Appendix-Audit; never paraphrase.
- **Vocabulary discipline.** Never "court-admissible"; use "defensible audit trail" or "structural rejection." Never "Ralph Wiggum Loop." Per PRD §14.
- **Context7 hint.** When in doubt about Hayabusa CLI flags, call `context7` for "Hayabusa csv-timeline" — the upstream README at https://github.com/Yamato-Security/hayabusa is the authoritative source. Per CICD_SPEC §12 + architecture §12.
- **LOC budget.** After this story `tools/log.py` is at ~260 LOC. Story-chainsaw-hunt adds ~130 LOC → final ~390 LOC, just under the 400 ceiling. If your draft exceeds ~280 LOC, factor the CSV-parsing logic into `_log_common.py::_parse_csv_with_truncation_detection`.
