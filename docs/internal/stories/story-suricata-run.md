# Story — suricata_run tool wrapper (Suricata)

**ID:** story-suricata-run
**Epic:** Epic 7 — Tool wrappers: log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata)
**Depends on:** story-zeek-run (skeleton: `_run_*` shape, `_NetworkResult`, `_network_common.py`)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or any MCP client)
**I want to** wrap Suricata's `-r <pcap>` mode as a typed MCP tool `suricata_run`
**So that** I receive a typed structured summary of the EVE JSON output (alert count, flow count, http count, dns count, tls count, eve_json path) — used as IDS-rule-driven complement to `zeek_run` (Zeek answers "what protocols ran"; Suricata answers "which rules fired"); load-bearing for the wardrive demo's "intercepted SMTP credentials" finding when an ET Open rule fires on the credential-leak pattern (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy).

---

## File modification map

- `src/silentwitness_mcp/tools/network.py` — UPDATE — add `suricata_run(input: SuricataInput) -> ToolResponse[SuricataRunResult]` wrapper (~180 LOC delta) reusing the subprocess + audit pattern from story-zeek-run (parallel helper `_run_suricata(pcap_path: Path, rules_path: Path, out_dir: Path, timeout_s: float) -> _NetworkResult`). Pydantic models: `SuricataInput(pcap_path: Path, rules_path: Path, out_dir: Path)`, `SuricataRunResult(eve_json_path: Path, eve_json_sha256: str, alert_count: int, flow_count: int, http_count: int, dns_count: int, tls_count: int, fileinfo_count: int, anomaly_count: int, stats_count: int, total_events: int, event_type_breakdown: dict[str, int])`.
- `src/silentwitness_mcp/tools/_network_common.py` — UPDATE — add `SURICATA_BIN = Path("/usr/bin/suricata")` (Ubuntu Noble universe install path) with fallback `/usr/local/bin/suricata`. Append `_NETWORK_CAVEATS["suricata_run"]` entries verbatim from `context/domain/04` §21 Suricata section.
- `src/silentwitness_mcp/server.py` — UPDATE — register `suricata_run` with the FastMCP `Server`.
- `install.sh` — UPDATE — add `install_suricata()` step. Per `context/.raw-design-research/03` line 161 + 218 + 274 + docs/.audit/06-sift-and-datasets-verification.md, Suricata is NOT pre-installed on SIFT 2026 but IS in **Ubuntu 24.04 (Noble) universe** — install directly via `apt install -y suricata` (no third-party repo needed; Suricata 7.x ships with Noble). Optionally `suricata-update` to fetch ET Open rules to `/var/lib/suricata/rules/suricata.rules`. Pin Suricata version (e.g., 7.x) for reproducibility.
- `tests/fixtures/network/suricata_eve_sample.json` — NEW — small EVE JSON (≤20 lines, JSONL format — one JSON object per line) mirroring the canonical Suricata event types: `alert` event (rule fired) + `flow` event + `http` event + `dns` event + `tls` event + `fileinfo` event + `anomaly` event + `stats` event.
- `tests/fixtures/network/suricata_minimal.rules` — NEW — a tiny `.rules` file (≤5 rules — `ET Open` shaped: e.g., `alert tls $HOME_NET any -> $EXTERNAL_NET any (msg:"TEST Cobalt Strike Default Cert"; tls.cert_subject; content:"CN=Major Cobalt Strike"; sid:1000001; rev:1;)`).
- `tests/unit/tools/test_network_suricata.py` — NEW — ≥6 behavioural test cases: (a) valid Suricata run produces `eve.json`, parsed into `SuricataRunResult` with `alert_count`+`flow_count`+`http_count`+`dns_count`+`tls_count` populated from the per-event-type tally, (b) Suricata not installed at `/usr/bin/suricata` returns `success=False` reason `SURICATA_NOT_INSTALLED` advisory pointing the agent at `install.sh`, (c) unregistered pcap path returns `success=False` reason `EVIDENCE_NOT_REGISTERED`, (d) **unregistered rules path returns `success=False` reason `EVIDENCE_NOT_REGISTERED`** — the rules file IS evidence (see Notes), (e) Suricata exits non-zero (malformed rules) returns `success=False` reason `TOOL_FAILED` with first 500 chars of stderr in advisories, (f) Suricata run produces no `eve.json` returns `success=False` reason `OUTPUT_PARSE_FAILED`. Subprocess mocked via `monkeypatch`.
- `tests/integration/tools/test_network_suricata_integration.py` — NEW — single e2e test invoking real `/usr/bin/suricata -r <tiny.pcap> -S <suricata_minimal.rules> -l <out-dir>` (skipped via `pytest.mark.skipif(not Path('/usr/bin/suricata').exists() and not Path('/usr/local/bin/suricata').exists())`).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered pcap at /evidence/case-001/wardrive.pcap
And   a registered rules file at /evidence/case-001/suricata.rules (registered with type=ids_rules in cases/case-001/evidence.json)
And   both files have SHA256 entries matching their current contents
And   /evidence/ is mounted ro,noexec,nosuid
And   /usr/bin/suricata (or /usr/local/bin/suricata) exists and is executable
When  the MCP tool suricata_run is called with SuricataInput(pcap_path=Path("/evidence/case-001/wardrive.pcap"), rules_path=Path("/evidence/case-001/suricata.rules"), out_dir=Path("/tmp/suricata-out/"))
Then  the response is ResponseEnvelope with success=True
And   data is a SuricataRunResult with eve_json_path == Path("/tmp/suricata-out/eve.json")
And   data.eve_json_sha256 is a 64-hex SHA256 of the eve.json bytes
And   data.alert_count == number of lines with "event_type":"alert"
And   data.flow_count == number of lines with "event_type":"flow"
And   data.http_count == number of lines with "event_type":"http"
And   data.dns_count == number of lines with "event_type":"dns"
And   data.tls_count == number of lines with "event_type":"tls"
And   data.fileinfo_count == number of lines with "event_type":"fileinfo"
And   data.anomaly_count == number of lines with "event_type":"anomaly"
And   data.stats_count == number of lines with "event_type":"stats"
And   data.total_events == count of all newline-delimited JSON objects in eve.json
And   data.event_type_breakdown is a dict[str, int] of every event_type seen → count (covers any types not in the typed fields above)
And   data_provenance.cmd_argv == ["/usr/bin/suricata", "-r", "/evidence/case-001/wardrive.pcap", "-S", "/evidence/case-001/suricata.rules", "-l", "/tmp/suricata-out/", "--runmode", "single", "-k", "none"]
And   data_provenance.stdout_path points to cases/case-001/audit/blobs/<audit_id>.txt holding the normalized stdout + eve.json SHA256 + per-event-type counts manifest
And   data_provenance.result_sha256 is the SHA256 of the normalized stdout+manifest
And   one JSONL line is appended to cases/case-001/audit/network.jsonl
And   caveats includes "Suricata alert event_type entries are rule matches — the rule SID + msg identifies the detection; corroborate against ET Open ruleset version (rules drift across releases)"
And   caveats includes "Suricata's flow event_type is similar to Zeek's conn.log but with rule-match decoration; cross-check with zeek_run for protocol parsing fidelity"
And   caveats includes "EVE JSON is one JSON object per line — use jq or line-by-line parse; the schema is documented at https://docs.suricata.io/en/latest/output/eve/eve-json-format.html"
And   corroboration includes a hint pointing at zeek_run for protocol-parsing complement on the same pcap

Given /usr/bin/suricata does NOT exist AND /usr/local/bin/suricata does NOT exist
When  suricata_run is called
Then  the response is ResponseEnvelope with success=False reason="SURICATA_NOT_INSTALLED"
And   advisories[0] contains "Suricata is NOT pre-installed on SIFT 2026 — run install.sh to add it (see context/.raw-design-research/03 §'Tools our install script MUST add')"
And   no subprocess is spawned

Given the pcap path is not registered in cases/<case_id>/evidence.json
When  suricata_run is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   advisories[0] contains "EVIDENCE_NOT_REGISTERED: <pcap_path>"
And   no Suricata subprocess is spawned

Given the rules_path is not registered in cases/<case_id>/evidence.json
When  suricata_run is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   advisories[0] contains "EVIDENCE_NOT_REGISTERED: <rules_path> — Suricata rules files ARE evidence and must be registered before use"
And   no Suricata subprocess is spawned

Given either the pcap OR the rules file has a SHA256 mismatch against its manifest entry
When  suricata_run is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"
And   advisories names which file mismatched

Given /evidence/ is mounted without one of ro / noexec / nosuid
When  suricata_run is called
Then  the response is ResponseEnvelope with success=False reason="MOUNT_NOT_RO_NOEXEC_NOSUID"

Given Suricata exits with a non-zero return code (e.g., malformed rules file)
When  suricata_run is called against valid registered paths
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL line records exit_code != 0 and elapsed_ms

Given Suricata exits 0 but no eve.json was produced in out_dir
When  suricata_run is called
Then  the response is ResponseEnvelope with success=False reason="OUTPUT_PARSE_FAILED"
And   advisories[0] contains "eve.json missing from <out_dir> after Suricata exit 0 — verify suricata.yaml outputs.eve-log.enabled: yes"

Given Suricata exceeds the 900s timeout
When  suricata_run is called
Then  the subprocess is terminated (SIGKILL after SIGTERM grace)
And   the response is ResponseEnvelope with success=False reason="TOOL_TIMEOUT"
```

---

## Shell verification

```bash
# Unit tests pass with ≥6 behavioural cases
uv run pytest tests/unit/tools/test_network_suricata.py -v

# Integration test skipped on non-SIFT runners
uv run pytest tests/integration/tools/test_network_suricata_integration.py -v

# Lint + format + strict types
uv run ruff check src/silentwitness_mcp/tools/network.py src/silentwitness_mcp/tools/_network_common.py
uv run ruff format --check src/silentwitness_mcp/tools/network.py src/silentwitness_mcp/tools/_network_common.py
uv run mypy --strict src/silentwitness_mcp/tools/network.py src/silentwitness_mcp/tools/_network_common.py

# File-size guard — aggregate cap across 2 network tools ≤400
wc -l src/silentwitness_mcp/tools/network.py | awk '{ if ($1 > 400) exit 1 }'

# Coverage floor for tools/network.py per CICD_SPEC §8.1 (85% target)
uv run coverage run -m pytest tests/unit/tools/test_network_suricata.py tests/unit/tools/test_network_zeek.py
uv run coverage report --include="src/silentwitness_mcp/tools/network.py,src/silentwitness_mcp/tools/_network_common.py" --fail-under=85

# install.sh provisions Suricata
grep -E "suricata" install.sh | grep -iE "(apt install|/usr/bin/suricata|/usr/local/bin/suricata)"
# Must output at least 1 line referencing the install

# §13 banned patterns: no shell=True, no mock/fake/dummy in src/
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated|shell=True)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **Suricata is NOT pre-installed on SIFT 2026.** Verified `context/.raw-design-research/03` §Network forensics line 161 ("Suricata **NOT installed** — no `.sls`") + §"Tools our install script MUST add" line 218 ("**Suricata** — `apt install suricata` (Noble has it in universe)") + line 274. The wrapper MUST check `SURICATA_BIN.exists()` (with fallback to `/usr/local/bin/suricata` for source-built installs) as the first action after evidence-registry checks and fail with structured `SURICATA_NOT_INSTALLED` advisories pointing at `install.sh`. This is the structural defense against the model fabricating a Suricata output.
- **install.sh delta** (per architecture §3 line 270 + Epic 1 + `context/.raw-design-research/03` line 218). The install script must:
  1. `apt update && apt install -y suricata` (Ubuntu Noble universe has Suricata 7.x).
  2. Optionally run `suricata-update` to fetch ET Open rules to `/var/lib/suricata/rules/suricata.rules` (documents the default rules location; the wrapper does NOT consume this default — see "rules file IS evidence" below).
  3. Verify the binary: `/usr/bin/suricata --version` exits 0.
  4. The wrapper's `SURICATA_BIN` constant in `_network_common.py` checks `/usr/bin/suricata` first then `/usr/local/bin/suricata` — the install script comments which path it landed on.
- **Suricata invocation pattern** (per `context/domain/04` §21 + verified flag catalog). Primary mode is `suricata -r <pcap> -S <rules> -l <out-dir>`. Force these flags in every invocation: `--runmode single` (single-threaded; deterministic across runs — multi-threaded mode produces non-deterministic event ordering in eve.json which breaks the citation-gate SHA256 reproducibility), `-k none` (disable checksum checking; many evidence pcaps have offloaded/missing checksums and Suricata drops them by default), `-S <rules>` (load ONLY the specified rules file — disables config-default rule loading, ensuring the run is bounded by the registered rules file alone). Build `cmd_argv` deterministic for the audit log.
- **Rules file IS evidence — load-bearing distinction.** Unlike Chainsaw (where the mapping file is tool config) and Hayabusa (where the rules dir is a managed install asset), Suricata rules ARE evidence: the rules drive WHICH alerts fire, so the registered SHA256 of the rules file is part of the reproducibility chain. If two `suricata_run` invocations cite the same audit_id but the rules file changed underneath, the alert set would silently differ — that is the exact failure mode the evidence registry exists to prevent (architecture §4.10). The wrapper MUST call `evidence_registry.assert_registered(rules_path)` AND `evidence_registry.verify_hash(rules_path)` in addition to the same calls for the pcap. Both files registered → proceed. Either missing or tampered → fail closed with the offending path in the advisory. The agent must `register_evidence` the `.rules` file with `type=ids_rules` BEFORE calling `suricata_run` — document this in the module docstring as a load-bearing contract.
- **EVE JSON parsing** (per `context/domain/04` §21.2 lines 1167–1183). The output is `<out_dir>/eve.json` — one JSON object per line, with `event_type` field. Iterate line-by-line; for each line `json.loads`; tally per-event-type counts. Typed counter fields cover the common event_types (`alert`, `flow`, `http`, `dns`, `tls`, `fileinfo`, `anomaly`, `stats`); the `event_type_breakdown: dict[str, int]` catchall covers any others (smb, ssh, ftp, smtp, etc. — per `context/domain/04` §21.2). Do NOT load the entire eve.json into memory — for large pcaps this file can be GB-sized; stream line-by-line with `with open(eve_json_path, 'r') as f: for line in f:`.
- **Audit-blob manifest.** Suricata produces multiple output files (`eve.json`, `fast.log`, `stats.log`, `suricata.log`). The eve.json is the canonical event stream; the others are summary/operational logs. Audit blob format: deterministic manifest with `eve.json` SHA256 + per-event-type counts + each ancillary log filename + size. SHA256 of that manifest is `result_sha256`. Citations downstream reference the eve.json by line number + the manifest's eve_json_sha256 (the citation gate's `OUTPUT_HASH_MISMATCH` check uses this).
- **Subprocess pattern.** `_run_suricata(pcap_path: Path, rules_path: Path, out_dir: Path, timeout_s: float = 900.0) -> _NetworkResult` uses `asyncio.create_subprocess_exec(*argv, stdout=PIPE, stderr=PIPE)` with `asyncio.wait_for(proc.communicate(), timeout=timeout_s)`. On `asyncio.TimeoutError`: `proc.terminate()`, then after a 5s grace `proc.kill()`, return `TOOL_TIMEOUT`. Capture stderr first 500 chars for `TOOL_FAILED` advisory. Reuses `_NetworkResult` shape from story-zeek-run.
- **Evidence-registry call ordering** (per architecture §4.10). First action: `await evidence_registry.assert_registered(pcap_path)` AND `await evidence_registry.assert_registered(rules_path)`. If either is not registered, return `EVIDENCE_NOT_REGISTERED` with the offending path named. Second: `await evidence_registry.verify_hash(pcap_path)` AND `await evidence_registry.verify_hash(rules_path)` → `EVIDENCE_TAMPERED` (with offending path). Third: `mount.assert_safe_options("/evidence")` → `MOUNT_NOT_RO_NOEXEC_NOSUID`. Fourth: `SURICATA_BIN.exists() or (/usr/local/bin/suricata).exists()` → `SURICATA_NOT_INSTALLED`. Fifth: `out_dir.mkdir(parents=True, exist_ok=True)`. Only then spawn the subprocess.
- **Caveats — verbatim discipline** (per architecture §4.3). Source from `context/domain/04` §21 (Suricata architecture + EVE JSON). Exact strings in `_NETWORK_CAVEATS["suricata_run"]`:
  - `"Suricata alert event_type entries are rule matches — the rule SID + msg identifies the detection; corroborate against ET Open ruleset version (rules drift across releases)"`
  - `"Suricata's flow event_type is similar to Zeek's conn.log but with rule-match decoration; cross-check with zeek_run for protocol parsing fidelity"`
  - `"EVE JSON is one JSON object per line — use jq or line-by-line parse; the schema is documented at https://docs.suricata.io/en/latest/output/eve/eve-json-format.html"`
  - `"--runmode single is forced for deterministic event ordering; multi-threaded mode would break SHA256 reproducibility across runs on the same pcap"`
  Caveats appear in the report's Appendix-Audit; never paraphrase.
- **Zeek + Suricata are complementary, not redundant.** Per `context/domain/04` §21 lead-in. Zeek answers "what protocols ran in this pcap" (protocol-aware parsing → structured logs). Suricata answers "which rules fired on this pcap" (signature-driven detection → alerts). The `corroboration` field on the envelope MUST surface this — `["if suricata_run produced 0 alerts on a pcap, run zeek_run for protocol-aware coverage (notice.log + weird.log may surface anomalies Suricata's rules miss)"]`. The investigator agent runs both during the wardrive demo; the critic CHALLENGE step at 4:00–4:30 corroborates a Suricata alert against the Zeek flow that triggered it.
- **No shell interpolation** (per architecture §2 trust boundary 2). Build `cmd_argv` as `list[str]`. Never `shell=True`.
- **Vocabulary discipline.** Never "court-admissible" — use "defensible audit trail" or "structural rejection." Never "Ralph Wiggum Loop." Per PRD §14.
- **Context7 hint.** When in doubt about Suricata CLI flags or EVE JSON schema, call `context7` for "Suricata EVE JSON" — upstream docs at https://docs.suricata.io/ are authoritative. Per CICD_SPEC §12.
- **LOC budget tracking** (per architecture §4.2 + CICD_SPEC §6.1). After this story `tools/network.py` reaches ~360 LOC across both wrappers (zeek_run ~180 + suricata_run ~180). Aggregate is under the 400 ceiling. If your draft exceeds 200 LOC for this story alone, factor the EVE-JSON tallying logic into `_network_common.py::_tally_eve_events`.
