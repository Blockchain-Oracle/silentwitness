# Story — zeek_run tool wrapper (Zeek)

**ID:** story-zeek-run
**Epic:** Epic 7 — Tool wrappers: log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata)
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-audit-logger, story-evidence-registry, story-output-normalizer
**Estimate:** ~1.5h (skeleton story for the network family — first `network.py` wrapper; story-suricata-run reuses the subprocess + parse + audit pattern)
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Zeek's `-r <pcap>` mode as a typed MCP tool `zeek_run`
**So that** the investigator agent can decompose a registered pcap into Zeek's structured log set (`conn.log`, `http.log`, `dns.log`, `ssl.log`, `files.log`, `x509.log`, `notice.log`, `weird.log`) over a typed contract — load-bearing for the demo's network-corroboration moment (the wardrive pcap → `intercepted SMTP credentials` finding) and the critic CHALLENGE resolution at 4:00–4:30 (`zeek -r /evidence/captures/wardrive.pcap` per architecture §5.5 + demo storyboard) (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Audit Trail Quality).

This is the **skeleton story** for Epic 7's network family — it lands the `_run_zeek` async subprocess helper, the shared `_NetworkResult` adapter, the Zeek-TSV log parser, and the Pydantic output-model pattern that `suricata_run` (the next network story) reuses.

---

## File modification map

- `src/silentwitness_mcp/tools/network.py` — NEW — module skeleton + first wrapper. Docstring cites `architecture.md` §4.2 row 18 (`zeek_run`) + `context/.raw-design-research/03` §Network forensics line 160 (Zeek NOT pre-installed) + `context/domain/04` §20 (Zeek architecture + log catalog). Public API: `zeek_run(input: ZeekInput) -> ToolResponse[ZeekRunResult]`. Private helpers: `_run_zeek(pcap_path: Path, out_dir: Path, timeout_s: float) -> _NetworkResult` (shared shape with `_run_suricata` from story-suricata-run — get the signature right HERE), `_inventory_zeek_logs(log_dir: Path) -> dict[str, ZeekLogInfo]` (enumerates `*.log` files in the output dir, returns per-log line count + SHA256 + path), `_NetworkResult` dataclass (`exit_code`, `stdout`, `stderr`, `elapsed_ms`, `audit_id`, `output_dir`, `output_dir_manifest_sha256`). Pydantic models: `ZeekInput(pcap_path: Path, out_dir: Path)`, `ZeekLogInfo(path: Path, line_count: int, sha256: str)`, `ZeekRunResult(log_dir: Path, conn_log: ZeekLogInfo | None, http_log: ZeekLogInfo | None, dns_log: ZeekLogInfo | None, ssl_log: ZeekLogInfo | None, files_log: ZeekLogInfo | None, x509_log: ZeekLogInfo | None, notice_log: ZeekLogInfo | None, weird_log: ZeekLogInfo | None, other_logs: dict[str, ZeekLogInfo], total_logs: int, total_lines: int)`. Target ≤180 LOC after this story (leaves ~220 LOC for `suricata_run` under the 400-LOC ceiling per CICD_SPEC §6.1).
- `src/silentwitness_mcp/tools/_network_common.py` — NEW — shared constants: `ZEEK_BIN = Path("/usr/local/bin/zeek")` (default install location; falls back to `/opt/zeek/bin/zeek` per the OpenSUSE repo path documented in `context/.raw-design-research/03` line 217), default timeout 900s (pcap decode is slower than log parsing), `NetworkFailureReason` enum (`EVIDENCE_NOT_REGISTERED`, `EVIDENCE_TAMPERED`, `MOUNT_NOT_RO_NOEXEC_NOSUID`, `ZEEK_NOT_INSTALLED`, `SURICATA_NOT_INSTALLED`, `TOOL_FAILED`, `TOOL_TIMEOUT`, `OUTPUT_PARSE_FAILED`, `NO_LOGS_PRODUCED`), `_NETWORK_CAVEATS` per-tool caveat catalog (entries added per story). ~80 LOC.
- `src/silentwitness_mcp/server.py` — UPDATE — register `zeek_run` with the FastMCP `Server`.
- `install.sh` — UPDATE — add `install_zeek()` step. Per `context/.raw-design-research/03` line 217 + line 274 + docs/.audit/06-sift-and-datasets-verification.md, Zeek is NOT pre-installed on SIFT 2026 and the canonical install on Ubuntu 24.04 is via the **OpenSUSE security:zeek repo** (xUbuntu_24.04 path) — that repo is the upstream-blessed source on Ubuntu Noble. Steps: add the `security:zeek` apt source for `xUbuntu_24.04`, import the matching GPG key, `apt update && apt install -y zeek`. Pin the Zeek version (e.g., 6.x or 7.x) — do NOT `apt install zeek-lts` if reproducibility is required across hackathon runs. Verify binary lands at `/usr/local/bin/zeek` (or `/opt/zeek/bin/zeek`); update `_network_common.py::ZEEK_BIN` if the path differs.
- `tests/fixtures/network/zeek_conn_sample.log` — NEW — small Zeek TSV `conn.log` (≤20 rows) mirroring the canonical Zeek schema (header + 4-tuple + service + duration + bytes + state).
- `tests/fixtures/network/zeek_dns_sample.log` — NEW — small Zeek TSV `dns.log` (≤10 rows).
- `tests/unit/tools/test_network_zeek.py` — NEW — ≥6 behavioural test cases: (a) valid `zeek -r <pcap>` run produces a log dir containing `conn.log`+`dns.log`+`http.log`, parsed into `ZeekRunResult` with per-log line counts + SHA256s, (b) Zeek not installed at `/usr/local/bin/zeek` returns `success=False` reason `ZEEK_NOT_INSTALLED` advisory pointing at `install.sh`, (c) unregistered pcap path returns `success=False` reason `EVIDENCE_NOT_REGISTERED`, (d) SHA256 mismatch on the pcap returns `success=False` reason `EVIDENCE_TAMPERED`, (e) Zeek exits non-zero (e.g., truncated pcap) returns `success=False` reason `TOOL_FAILED` with first 500 chars of stderr in advisories, (f) Zeek run produces no `*.log` files (e.g., empty pcap) returns `success=False` reason `NO_LOGS_PRODUCED` with advisory "no protocol activity detected in pcap". Subprocess mocked via `monkeypatch` on `asyncio.create_subprocess_exec`.
- `tests/integration/tools/test_network_zeek_integration.py` — NEW — single e2e test invoking real `/usr/local/bin/zeek -r <tiny.pcap>` against a 10-packet synthetic pcap fixture under `tests/fixtures/network/tiny.pcap` (skipped via `pytest.mark.skipif(not Path('/usr/local/bin/zeek').exists() and not Path('/opt/zeek/bin/zeek').exists())`).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered pcap at /evidence/case-001/wardrive.pcap
And   the pcap is registered in cases/case-001/evidence.json with a SHA256 matching its current content
And   /evidence/ is mounted ro,noexec,nosuid (mount validation passes)
And   /usr/local/bin/zeek (or /opt/zeek/bin/zeek) exists and is executable
When  the MCP tool zeek_run is called with ZeekInput(pcap_path=Path("/evidence/case-001/wardrive.pcap"), out_dir=Path("/tmp/zeek-out/"))
Then  the response is ResponseEnvelope with success=True
And   data is a ZeekRunResult with log_dir == Path("/tmp/zeek-out/")
And   data.conn_log is a ZeekLogInfo with path=Path("/tmp/zeek-out/conn.log"), line_count > 0, sha256 == 64-hex SHA256 of the conn.log file bytes
And   data.dns_log is a ZeekLogInfo (or None if no DNS traffic was decoded)
And   data.http_log is a ZeekLogInfo (or None)
And   data.ssl_log is a ZeekLogInfo (or None)
And   data.files_log is a ZeekLogInfo (or None)
And   data.x509_log is a ZeekLogInfo (or None)
And   data.notice_log is a ZeekLogInfo (or None)
And   data.weird_log is a ZeekLogInfo (or None)
And   data.other_logs contains any additional log files (smb_files.log, kerberos.log, ssh.log, dhcp.log, etc.) keyed by filename without extension
And   data.total_logs == count of *.log files in log_dir
And   data.total_lines == sum of per-log line counts
And   data_provenance.cmd_argv == ["/usr/local/bin/zeek", "-r", "/evidence/case-001/wardrive.pcap"]
And   data_provenance.stdout_path points to cases/case-001/audit/blobs/<audit_id>.txt holding the Zeek stdout (banner stripped) + a manifest of log filenames + their SHA256s
And   data_provenance.result_sha256 is the SHA256 of the normalized stdout + manifest (deterministic across runs)
And   one JSONL line is appended to cases/case-001/audit/network.jsonl
And   caveats includes "Zeek base scripts produce a fixed set of logs; custom scripts (e.g., ja3.zeek for SSL fingerprints) must be loaded explicitly — absent custom scripts, ssl.log.ja3 will not populate"
And   caveats includes "Zeek runs from cwd by default — output landed in <out_dir>; weird.log entries are protocol anomalies, often the first hint of evasive C2 (corroborate with notice.log)"
And   caveats includes "conn.log is the spine — every flow has one entry; subsidiary logs (http.log, dns.log, ssl.log) join back via the uid field"
And   corroboration includes a hint pointing at suricata_run for IDS-rule-driven detection on the same pcap (Zeek answers 'what protocols ran'; Suricata answers 'which rules fired')

Given /usr/local/bin/zeek does NOT exist AND /opt/zeek/bin/zeek does NOT exist
When  zeek_run is called
Then  the response is ResponseEnvelope with success=False reason="ZEEK_NOT_INSTALLED"
And   advisories[0] contains "Zeek is NOT pre-installed on SIFT 2026 — run install.sh to add it (see context/.raw-design-research/03 §'Tools our install script MUST add')"
And   no subprocess is spawned

Given the pcap path is not registered in cases/<case_id>/evidence.json
When  zeek_run is called with that path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no Zeek subprocess is spawned (verified by mocked spawn count == 0)
And   one JSONL line is still written to network.jsonl recording the refusal

Given the registered pcap's current SHA256 does not match the manifest entry
When  zeek_run is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"
And   no Zeek subprocess is spawned

Given /evidence/ is mounted without one of ro / noexec / nosuid
When  zeek_run is called
Then  the response is ResponseEnvelope with success=False reason="MOUNT_NOT_RO_NOEXEC_NOSUID"
And   advisories includes the missing-flag list

Given Zeek exits with a non-zero return code (e.g., truncated pcap)
When  zeek_run is called against a valid registered path
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL line records exit_code != 0 and elapsed_ms

Given Zeek exceeds the 900s timeout
When  zeek_run is called
Then  the subprocess is terminated (SIGKILL after SIGTERM grace)
And   the response is ResponseEnvelope with success=False reason="TOOL_TIMEOUT"

Given Zeek runs successfully but produces no *.log files in out_dir (empty pcap)
When  zeek_run is called
Then  the response is ResponseEnvelope with success=False reason="NO_LOGS_PRODUCED"
And   advisories[0] contains "no protocol activity detected in pcap — verify the pcap is non-empty with `tcpdump -r <pcap> -c 5`"
```

---

## Shell verification

```bash
# Unit tests pass with ≥6 behavioural cases
uv run pytest tests/unit/tools/test_network_zeek.py -v

# Integration test skipped on non-SIFT, runs green when Zeek is installed
uv run pytest tests/integration/tools/test_network_zeek_integration.py -v

# Lint + format + strict types
uv run ruff check src/silentwitness_mcp/tools/network.py src/silentwitness_mcp/tools/_network_common.py
uv run ruff format --check src/silentwitness_mcp/tools/network.py src/silentwitness_mcp/tools/_network_common.py
uv run mypy --strict src/silentwitness_mcp/tools/network.py src/silentwitness_mcp/tools/_network_common.py
# All three must exit 0

# File-size guard — aggregate cap across 2 network tools ≤400
wc -l src/silentwitness_mcp/tools/network.py | awk '{ if ($1 > 400) exit 1 }'

# Coverage floor for tools/network.py per CICD_SPEC §8.1 (85% target)
uv run coverage run -m pytest tests/unit/tools/test_network_zeek.py
uv run coverage report --include="src/silentwitness_mcp/tools/network.py,src/silentwitness_mcp/tools/_network_common.py" --fail-under=85
# Must exit 0

# install.sh provisions Zeek
grep -E "zeek" install.sh | grep -iE "(apt install zeek|/opt/zeek|/usr/local/bin/zeek)"
# Must output at least 1 line referencing the install

# §13 banned patterns: no shell=True, no mock/fake/dummy in src/
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated|shell=True)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **Zeek is NOT pre-installed on SIFT 2026.** Verified `context/.raw-design-research/03` §Network forensics line 160 ("Zeek **NOT installed** — no `.sls`") + §"Tools our install script MUST add" line 217 + line 274 ("**Zeek + Suricata** (if our wedge touches pcap) — `apt install`"). The wrapper MUST check `ZEEK_BIN.exists()` (with fallback to `/opt/zeek/bin/zeek` for source-built installs) as the first action after evidence-registry checks and fail with structured `ZEEK_NOT_INSTALLED` advisories pointing at `install.sh`. This is a structural defense against the model running `apt install zeek` itself (which would fail without sudo) or fabricating a Zeek output.
- **install.sh delta** (per architecture §3 line 270 + Epic 1 + `context/.raw-design-research/03` line 217). The install script must:
  1. Add the OpenSUSE security:zeek repo via `echo 'deb http://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/ /' | sudo tee /etc/apt/sources.list.d/security:zeek.list` (the canonical path per `context/.raw-design-research/03` line 217) AND import the matching GPG key — OR fall back to Ubuntu Noble universe if version requirements allow.
  2. `apt update && apt install -y zeek` (or version-pinned `zeek-<ver>`).
  3. Verify the binary: `/usr/local/bin/zeek --version` exits 0 (or `/opt/zeek/bin/zeek --version` depending on the package's install prefix).
  4. The wrapper's `ZEEK_BIN` constant in `_network_common.py` checks `/usr/local/bin/zeek` first then `/opt/zeek/bin/zeek` — the install script comments which path it landed on so the wrapper's fallback is deterministic.
- **Zeek invocation pattern** (per `context/domain/04` §20 + verified flag catalog). Primary mode is `zeek -r <pcap>`. Zeek runs from the current working directory (`out_dir`); set `cwd=out_dir` in `asyncio.create_subprocess_exec` so the logs land where the caller expects. Force `-C` is OPTIONAL (continues on checksum errors — useful for evidence pcaps where checksums may be off) — current decision: include `-C` to maximize coverage on real captures; document the choice in the caveat ("conn.log entries derived from packets with bad checksums included via -C; cross-check with weird.log for protocol anomalies"). Default flags: `["zeek", "-r", str(pcap_path), "-C"]`. **DO NOT use `-i <interface>`** — that's live capture, not pcap replay; only `-r` for offline analysis.
- **Log catalog enumeration.** After `zeek -r` returns exit 0, enumerate `out_dir/*.log` files. Per `context/domain/04` §20.3–§20.11, the base scripts produce: `conn.log` (the spine — every flow), `http.log`, `dns.log`, `ssl.log`, `files.log`, `x509.log`, `notice.log`, `weird.log`, plus optionally `ssh.log`, `smb_files.log`, `smb_mapping.log`, `kerberos.log`, `rdp.log`, `dhcp.log`, `ftp.log`, `smtp.log`, `irc.log`, `dpd.log`, `loaded_scripts.log`, `software.log`, `tunnel.log`, `intel.log`, `signatures.log`. The Pydantic model has typed fields for the canonical eight (conn/http/dns/ssl/files/x509/notice/weird) and a `dict[str, ZeekLogInfo] other_logs` catchall for the rest, keyed by basename without extension.
- **Line counting + SHA256.** For each `*.log` file, count newline-terminated rows (`sum(1 for _ in open(path, 'rb'))`) and SHA256 the file bytes (no normalization for Zeek logs — they are evidence-derived, not tool-banner-noisy). The per-log SHA256 + line count is what citation gate cites later — the citation references a specific log file by name, not the Zeek run as a whole.
- **Audit-blob manifest.** Unlike single-stream tools (Vol3, EvtxECmd, Hayabusa, Chainsaw), Zeek produces a **directory** of logs, not a single stdout. The audit blob at `cases/<case_id>/audit/blobs/<audit_id>.txt` is a deterministic manifest: one line per `*.log` file in the format `<filename> <sha256> <line_count>`, sorted by filename. SHA256 of that manifest is the `result_sha256`. Citations downstream reference both the manifest (the run identity) and the per-log SHA256 (the specific log file's contents). Document this layered scheme in the module docstring — it's a departure from the single-blob pattern in `tools/log.py` and `tools/memory.py`.
- **Subprocess pattern.** `_run_zeek(pcap_path: Path, out_dir: Path, timeout_s: float = 900.0) -> _NetworkResult` uses `asyncio.create_subprocess_exec(*argv, stdout=PIPE, stderr=PIPE, cwd=out_dir)` with `asyncio.wait_for(proc.communicate(), timeout=timeout_s)`. On `asyncio.TimeoutError`: `proc.terminate()`, then after a 5s grace `proc.kill()`, return `TOOL_TIMEOUT`. Capture stderr first 500 chars for `TOOL_FAILED` advisory. **Get the signature right HERE — story-suricata-run depends on the `_NetworkResult` shape.**
- **Evidence-registry call ordering** (per architecture §4.10). First action: `await evidence_registry.assert_registered(pcap_path)`. If not registered, return `ToolResponse(success=False, advisories=["EVIDENCE_NOT_REGISTERED: <path>"], …)` — do NOT spawn Zeek. Second: `await evidence_registry.verify_hash(pcap_path)` → `EVIDENCE_TAMPERED`. Third: `mount.assert_safe_options("/evidence")` → `MOUNT_NOT_RO_NOEXEC_NOSUID`. Fourth: `ZEEK_BIN.exists() or (/opt/zeek/bin/zeek).exists()` → `ZEEK_NOT_INSTALLED`. Fifth: `out_dir.mkdir(parents=True, exist_ok=True)`. Only then spawn the subprocess.
- **NO_LOGS_PRODUCED detection.** After Zeek exits 0, if the enumerated log count is 0, return `success=False` reason `NO_LOGS_PRODUCED`. An empty `out_dir` after a successful Zeek run means the pcap had no decodable protocol activity — surface this distinctly so the agent can revise its hypothesis (the pcap may be encrypted-tunnel-only, or completely empty). Distinct from `TOOL_FAILED` (which indicates Zeek itself failed). The advisory points the agent at `tcpdump -r <pcap> -c 5` as the sanity-check command.
- **Skeleton helpers MUST be reusable.** `_run_zeek` returns `_NetworkResult` — the same shape `_run_suricata` returns. The `_inventory_zeek_logs` helper is Zeek-specific (Suricata produces `eve.json`, not a log dir). The constants in `_network_common.py` cover both tools. Get the `_NetworkResult` signature right HERE — story-suricata-run is written assuming it exists.
- **Caveats — verbatim discipline** (per architecture §4.3). Source from `context/domain/04` §20 (Zeek architecture + log catalog). Exact strings in `_NETWORK_CAVEATS["zeek_run"]`:
  - `"Zeek base scripts produce a fixed set of logs; custom scripts (e.g., ja3.zeek for SSL fingerprints) must be loaded explicitly — absent custom scripts, ssl.log.ja3 will not populate"`
  - `"Zeek runs from cwd by default — output landed in <out_dir>; weird.log entries are protocol anomalies, often the first hint of evasive C2 (corroborate with notice.log)"`
  - `"conn.log is the spine — every flow has one entry; subsidiary logs (http.log, dns.log, ssl.log) join back via the uid field"`
  - `"-C flag includes packets with bad checksums; cross-check weird.log for protocol anomalies before treating noisy conn.log entries as ground truth"`
  Caveats appear in the report's Appendix-Audit; never paraphrase.
- **No shell interpolation** (per architecture §2 trust boundary 2). Build `cmd_argv` as `list[str]` and pass to `create_subprocess_exec`. Never use `subprocess.run(..., shell=True)`. The pcap path and out_dir go in as separate argv elements.
- **Vocabulary discipline.** Never "court-admissible" — use "defensible audit trail" or "structural rejection." Never "Ralph Wiggum Loop." Per PRD §14.
- **Context7 hint.** When in doubt about Zeek CLI flags or log schemas, call `context7` for "Zeek base scripts" — upstream docs at https://docs.zeek.org/ are authoritative. Per CICD_SPEC §12.
- **LOC budget tracking** (per architecture §4.2 line 321 + CICD_SPEC §6.1). After this story `tools/network.py` should sit at ~180 LOC. Story-suricata-run adds ~200 LOC → aggregate ~380 LOC at epic close. If your draft exceeds ~200 LOC for this story alone, factor the manifest-building logic into `_network_common.py::_build_log_manifest`.
