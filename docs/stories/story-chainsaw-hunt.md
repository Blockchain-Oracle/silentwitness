# Story — chainsaw_hunt tool wrapper (Chainsaw)

**ID:** story-chainsaw-hunt
**Epic:** Epic 7 — Tool wrappers: log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata)
**Depends on:** story-parse-evtx (skeleton: `_run_native_log_tool`, `_normalize_and_store`, `_LogResult`, `_log_common.py`), story-hayabusa-timeline (extends `_log_common.py`)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or any MCP client)
**I want to** wrap Chainsaw's `hunt` subcommand as a typed MCP tool `chainsaw_hunt`
**So that** I receive a typed list of `ChainsawHit` rows with Sigma-rule detections + Chainsaw-native rule hits + MITRE ATT&CK mappings — used as a **cross-engine corroboration** for Hayabusa (per `context/domain/06` §7.2 "different mappings and minor parser differences mean Hayabusa and Chainsaw occasionally fire different rules on the same input. Cross-running is cheap and reduces blind spots"), load-bearing for the critic CHALLENGE at 4:00–4:30 (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Autonomous Execution Quality — closed-loop self-correction depends on the second opinion).

---

## File modification map

- `src/silentwitness_mcp/tools/log.py` — UPDATE — add `chainsaw_hunt(input: ChainsawInput) -> ToolResponse[ChainsawOutput]` wrapper (~120 LOC delta) reusing `_run_native_log_tool` from story-hayabusa-timeline. Pydantic models: `ChainsawInput(evtx_dir: Path, json_out: Path, sigma_rules_dir: Path = Path("/opt/sigma"), mapping_file: Path = Path("/opt/chainsaw/mappings/sigma-event-logs-all.yml"), level: Literal["info", "low", "medium", "high", "critical"] | None = None)`, `ChainsawHit(Name: str, Authors: list[str], Tags: list[str], Channel: str, EventID: int, RecordID: int, Timestamp: datetime, MitreAttack: list[str], FoundInLine: dict[str, Any], RuleLevel: str, RuleSource: Literal["sigma", "chainsaw"])`, `ChainsawOutput(hits: list[ChainsawHit], row_count: int, truncated: bool, rules_loaded: int | None)`.
- `src/silentwitness_mcp/tools/_log_common.py` — UPDATE — add `CHAINSAW_BIN = Path("/opt/chainsaw/chainsaw")`, `CHAINSAW_MAPPING_DEFAULT = Path("/opt/chainsaw/mappings/sigma-event-logs-all.yml")`, `SIGMA_RULES_DIR = Path("/opt/sigma")`, extend `LogFailureReason` enum with `CHAINSAW_NOT_INSTALLED`, `CHAINSAW_MAPPING_MISSING`, `SIGMA_RULES_MISSING`, append `_LOG_CAVEATS["chainsaw_hunt"]` entries verbatim from `context/domain/06` §7.2 Limitations.
- `src/silentwitness_mcp/server.py` — UPDATE — register `chainsaw_hunt` with the FastMCP `Server`.
- `install.sh` — UPDATE — add `install_chainsaw()` step that `curl -L`s the Chainsaw release tarball from `https://github.com/WithSecureLabs/chainsaw/releases/download/v2.16.0/chainsaw_x86_64-unknown-linux-gnu.tar.gz` (Chainsaw pinned to **v2.16.0** — verified SHA256 in docs/.audit/06-sift-and-datasets-verification.md) to `/opt/chainsaw/`, and `git clone`s the upstream Sigma corpus to `/opt/sigma/` per `context/.raw-design-research/03` §"Tools our install script MUST add" line 272 + line 279.
- `tests/fixtures/log/chainsaw_sample.json` — NEW — small JSON (≤10 rows) mirroring real Chainsaw `hunt --json` output (one Sigma hit + one Chainsaw-native hit + one multi-tag hit). Source schema: https://github.com/WithSecureLabs/chainsaw/blob/master/docs/output.md.
- `tests/unit/tools/test_log_chainsaw.py` — NEW — ≥6 behavioural test cases: (a) valid Chainsaw JSON parses into `ChainsawOutput` with `Authors` and `Tags` and `MitreAttack` correctly split into `list[str]`, (b) `level="high"` argument passes `--level high,critical` correctly (Chainsaw uses comma-joined), (c) Chainsaw not installed at `/opt/chainsaw/chainsaw` returns `success=False` reason `CHAINSAW_NOT_INSTALLED` advisory pointing the agent at `install.sh`, (d) mapping file missing returns `success=False` reason `CHAINSAW_MAPPING_MISSING`, (e) Sigma rules dir missing returns `success=False` reason `SIGMA_RULES_MISSING`, (f) Chainsaw exits non-zero returns `success=False` reason `TOOL_FAILED`. Subprocess mocked via `monkeypatch`.
- `tests/integration/tools/test_log_chainsaw_integration.py` — NEW — single e2e test invoking real `/opt/chainsaw/chainsaw hunt -e <evtx_fixture_dir> --sigma /opt/sigma --mapping /opt/chainsaw/mappings/sigma-event-logs-all.yml -j <out>` (skipped via `pytest.mark.skipif(not Path('/opt/chainsaw/chainsaw').exists())`).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered EVTX directory at /evidence/case-001/evtx/
And   /opt/chainsaw/chainsaw exists and is executable
And   /opt/chainsaw/mappings/sigma-event-logs-all.yml exists
And   /opt/sigma/ exists with ≥1 *.yml rule file
And   /evidence/ is mounted ro,noexec,nosuid
When  the MCP tool chainsaw_hunt is called with ChainsawInput(evtx_dir=Path("/evidence/case-001/evtx/"), json_out=Path("/tmp/chainsaw_out.json"))
Then  the response is ResponseEnvelope with success=True
And   data is a ChainsawOutput containing a list[ChainsawHit]
And   each ChainsawHit has typed fields: Name: str, Authors: list[str], Tags: list[str], Channel: str, EventID: int, RecordID: int, Timestamp: datetime (UTC), MitreAttack: list[str], FoundInLine: dict[str, Any], RuleLevel: str, RuleSource: Literal["sigma", "chainsaw"]
And   MitreAttack is the parsed list of T-codes extracted from Tags (e.g., ["T1059.001", "T1027"])
And   data_provenance.cmd_argv == ["/opt/chainsaw/chainsaw", "hunt", "-e", "/evidence/case-001/evtx/", "--sigma", "/opt/sigma", "--mapping", "/opt/chainsaw/mappings/sigma-event-logs-all.yml", "-j", "/tmp/chainsaw_out.json", "--quiet", "--no-color", "--metadata"]
And   data_provenance.stdout_path points to cases/case-001/audit/blobs/<audit_id>.txt holding the normalized JSON bytes
And   data_provenance.result_sha256 is a 64-hex SHA256 of the normalized JSON
And   one JSONL line is appended to cases/case-001/audit/log.jsonl
And   caveats includes "Chainsaw hunt operates on Windows EVTX only; analyse sub-commands cover ShimCache and SRUM but are not a general artifact framework"
And   caveats includes "Chainsaw is slightly slower than Hayabusa on identical workloads; different parser behaviour means the two engines occasionally fire different rules on the same input — cross-engine corroboration is the intended pattern"
And   corroboration includes a hint pointing at hayabusa_csv_timeline for cross-engine Sigma corroboration

Given /opt/chainsaw/chainsaw does NOT exist on this host
When  chainsaw_hunt is called
Then  the response is ResponseEnvelope with success=False reason="CHAINSAW_NOT_INSTALLED"
And   advisories[0] contains "Chainsaw is NOT pre-installed on SIFT 2026 — run install.sh to add it (see context/.raw-design-research/03 §'Tools our install script MUST add')"
And   no subprocess is spawned

Given /opt/chainsaw/mappings/sigma-event-logs-all.yml does not exist
When  chainsaw_hunt is called
Then  the response is ResponseEnvelope with success=False reason="CHAINSAW_MAPPING_MISSING"
And   advisories[0] points the agent at install.sh

Given /opt/sigma/ does not exist OR contains no *.yml files
When  chainsaw_hunt is called
Then  the response is ResponseEnvelope with success=False reason="SIGMA_RULES_MISSING"
And   advisories[0] points the agent at install.sh which runs git clone https://github.com/SigmaHQ/sigma /opt/sigma

Given ChainsawInput.level == "high"
When  chainsaw_hunt is called
Then  data_provenance.cmd_argv includes "--level" followed by "high,critical"
And   every ChainsawHit in the output has RuleLevel in {"high", "critical"}

Given the evtx_dir is not registered in cases/<case_id>/evidence.json
When  chainsaw_hunt is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no Chainsaw subprocess is spawned

Given Chainsaw exits with a non-zero return code
When  chainsaw_hunt is called
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
```

---

## Shell verification

```bash
# Unit tests pass with ≥6 behavioural cases
uv run pytest tests/unit/tools/test_log_chainsaw.py -v

# Integration test skipped on non-SIFT runners
uv run pytest tests/integration/tools/test_log_chainsaw_integration.py -v

# Lint + format + strict types
uv run ruff check src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
uv run ruff format --check src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
uv run mypy --strict src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py

# File-size guard — aggregate cap across 3 log tools ≤400
wc -l src/silentwitness_mcp/tools/log.py | awk '{ if ($1 > 400) exit 1 }'

# Coverage floor for tools/log.py per CICD_SPEC §8.1 (85% target)
uv run coverage run -m pytest tests/unit/tools/test_log_chainsaw.py tests/unit/tools/test_log_hayabusa.py tests/unit/tools/test_log_parse_evtx.py
uv run coverage report --include="src/silentwitness_mcp/tools/log.py,src/silentwitness_mcp/tools/_log_common.py" --fail-under=85

# install.sh provisions Chainsaw to the documented path
grep -E "chainsaw" install.sh | grep -E "/opt/chainsaw/"
# Must output at least 1 line referencing the install path

# §13 banned patterns: no shell=True, no mock/fake/dummy in src/
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated|shell=True)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **Chainsaw is NOT pre-installed on SIFT 2026.** Verified `context/.raw-design-research/03` §Threat hunting line 168 ("Chainsaw **NOT installed** (no `.sls`)") + §"Tools our install script MUST add" line 272 ("**Chainsaw** — same pattern from `WithSecureLabs/chainsaw`"). The wrapper MUST check `/opt/chainsaw/chainsaw`, `/opt/chainsaw/mappings/sigma-event-logs-all.yml`, and `/opt/sigma/` existence as the first action after evidence-registry checks and fail with structured advisories pointing the agent at `install.sh`. This is the structural defense against the model fabricating a Chainsaw output.
- **install.sh delta** (per architecture §3 line 270 + Epic 1 + `context/.raw-design-research/03` line 272). The install script must:
  1. `curl -L` the Chainsaw **v2.16.0** release tarball (version-pinned, SHA256-verified per docs/.audit/06-sift-and-datasets-verification.md) from `https://github.com/WithSecureLabs/chainsaw/releases/download/v2.16.0/chainsaw_x86_64-unknown-linux-gnu.tar.gz` to `/tmp/`, extract to `/opt/chainsaw/`, flatten the inner directory so the binary lands at `/opt/chainsaw/chainsaw` and the mappings land at `/opt/chainsaw/mappings/`.
  2. `chmod +x /opt/chainsaw/chainsaw`.
  3. `git clone https://github.com/SigmaHQ/sigma /opt/sigma` pinned to a tag/SHA (reproducibility per architecture §6 line 497).
  4. Verify the binary runs: `/opt/chainsaw/chainsaw --version` exits 0.
  5. Verify the mapping file exists: `test -f /opt/chainsaw/mappings/sigma-event-logs-all.yml`.
- **Chainsaw invocation pattern** (per `context/domain/06` §7.2 lines 1796–1807). Primary mode is `hunt -e <evtx_dir> --sigma <rules-dir> --mapping <mapping.yml> -j <out.json>`. Force these flags in every invocation: `--quiet` (suppress banner), `--no-color`, `--metadata` (include rule metadata — Authors, Tags, MitreAttack — in output; load-bearing for the typed Pydantic shape). When `level` is set, append `--level <comma-joined>` — Chainsaw expects comma-joined values when filtering multiple levels (high → "high,critical" per the project's convention of including critical when high is requested). Use `-j` (JSON) NOT `--csv` — the JSON output preserves the `FoundInLine` event payload as a nested object (required for `ChainsawHit.FoundInLine: dict[str, Any]` typing).
- **JSON output schema** (per Chainsaw docs at https://github.com/WithSecureLabs/chainsaw + `context/domain/06` §7.2 lines 1796–1825). Top-level: `[{group: str, kind: str, document: {...}, hits: [{rule: {name, authors[], tags[], level, ...}, timestamp, event: {...event xml fields...}}]}]`. The wrapper flattens the nested shape: one `ChainsawHit` per `(group, hit)` pair. `Tags` is the rule's `tags` array (e.g., `["attack.execution", "attack.t1059.001"]`); `MitreAttack` is extracted by parsing `T<digits>` tokens out of `Tags`. `Authors` is the rule's `authors` array. `RuleSource` is `"sigma"` when the rule came from `--sigma`, `"chainsaw"` when from native `-r rules/` (Chainsaw distinguishes these in the output `group` field — verify against the integration fixture before pinning the parsing logic). `Timestamp` is parsed from the event's `Event.System.TimeCreated.SystemTime` XPath. Map to typed Pydantic `ChainsawHit`.
- **Subprocess + audit pattern.** Reuse `_run_native_log_tool` from `_log_common.py` (landed in story-hayabusa-timeline). Same `_LogResult` shape, same `_normalize_and_store` audit-blob writer. The normalizer strips Chainsaw's banner + ANSI; SHA256 the normalized JSON bytes; persist at `cases/<case_id>/audit/blobs/<audit_id>.txt` per architecture §4.6.
- **Evidence-registry semantics for directories** (mirrors story-hayabusa-timeline). Chainsaw's `-e <dir>` operates on every `*.evtx` under the directory. The wrapper enumerates `*.evtx` and calls `evidence_registry.assert_registered` per file. ANY unregistered file → `EVIDENCE_NOT_REGISTERED` with the offending paths in advisories. Fail closed.
- **Mapping file is NOT evidence — it is tool config.** The mapping file (`sigma-event-logs-all.yml`) ships with Chainsaw; it is a static config file, not a registered evidence artifact. The existence check is sufficient. (Contrast with story-suricata-run where the rules file IS treated as evidence — see that story for the distinction.)
- **Caveats — verbatim discipline.** Source from `context/domain/06` §7.2 (Limitations section). Exact strings in `_LOG_CAVEATS["chainsaw_hunt"]`:
  - `"Chainsaw hunt operates on Windows EVTX only; analyse sub-commands cover ShimCache and SRUM but are not a general artifact framework"`
  - `"Chainsaw is slightly slower than Hayabusa on identical workloads; different parser behaviour means the two engines occasionally fire different rules on the same input — cross-engine corroboration is the intended pattern"`
  - `"Chainsaw needs a mapping YAML to translate Sigma field names to the EVTX event XML structure; absent or wrong mapping → silent zero-detection result"`
  Per architecture §4.3, caveats are surfaced in the report's Appendix-Audit and the Sigma-tag-driven entity gate cross-references the `MitreAttack` list against cited spans.
- **Cross-engine corroboration is the wedge.** The reason `chainsaw_hunt` exists alongside `hayabusa_csv_timeline` is the closed-loop critic at 4:00–4:30 of the demo — when Hayabusa fires a CRITICAL rule, the critic's CHALLENGE verdict triggers a Chainsaw run as second opinion. Per `context/domain/06` §7.2 line 1827 ("Why investigators run both. Different mappings and minor parser differences mean Hayabusa and Chainsaw occasionally fire different rules on the same input. Cross-running is cheap and reduces blind spots"). The `corroboration` field on the envelope MUST surface this hint — `["if hayabusa_csv_timeline fired no detections, also run chainsaw_hunt for cross-engine corroboration", "if hayabusa_csv_timeline fired a critical, run chainsaw_hunt as second opinion before staging as a finding"]`.
- **Vocabulary discipline.** Never "court-admissible" — use "defensible audit trail" or "structural rejection." Never "Ralph Wiggum Loop." Per PRD §14.
- **Context7 hint.** When in doubt about Chainsaw CLI flags or JSON output schema, call `context7` for "Chainsaw hunt subcommand" — upstream README at https://github.com/WithSecureLabs/chainsaw is authoritative. Per CICD_SPEC §12.
- **LOC budget.** After this story `tools/log.py` reaches ~390 LOC across all 3 wrappers (parse_evtx ~140 + hayabusa ~130 + chainsaw ~120). If your draft exceeds 400, factor the JSON-flattening logic into `_log_common.py::_flatten_chainsaw_json` before the file-size guard fires.
