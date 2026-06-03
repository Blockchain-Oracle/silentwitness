# Story — regripper_run tool wrapper (RegRipper 3.0 / rip.pl)

**ID:** story-regripper
**Epic:** Epic 6 — Tool wrappers: disk + registry (EZ Tools + RegRipper)
**Depends on:** story-response-envelope, story-evidence-registry, story-audit-logger, story-fastmcp-server-bootstrap
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or disk specialist subagent)
**I want to** call `regripper_run` with a registered registry hive and a named RegRipper plugin and receive the plugin's structured-text output captured under a stable audit ID
**So that** registry-resident artifacts that no EZ Tool surfaces (UserAssist run history, AppCompatibility shim flags, USB device first/last connect, computer name, time zone, BAM/DAM execution evidence, etc.) become typed, cited findings — the bulk of Hours 6–14 of any registry-heavy IR engagement per encyclopedia §15 + §22.

---

## File modification map

- `src/silentwitness_mcp/tools/registry.py` — NEW — module docstring citing `architecture.md` §4.2 row 19 + `context/.raw-design-research/03` line 95 (RegRipper path) + `context/domain/06` §6.1; Pydantic input `RegripperInput(hive_path: Path, plugin_name: str)`; Pydantic output `RegripperOutput(hive_path: str, plugin_name: str, output_text: str, parsed_keys: list[str], line_count: int)`; helper `_list_plugins() -> set[str]` (caches `rip.pl -l` output once per process); helper `_assert_plugin_known(name)`; `regripper_run(input: RegripperInput) -> ToolResponse[RegripperOutput]`. Single-tool file: ~140 LOC (budget ≤200 LOC per architecture §4.2 LOC catalog).
- `tests/unit/tools/test_registry_regripper.py` — NEW — ≥6 behavioral tests covering valid plugin, unknown plugin, unregistered hive, malformed hive, mount-flag failure, hash-mismatch path. Uses `tests/fixtures/registry/rip_compname.txt` as a captured rip.pl stdout fixture.
- `tests/fixtures/registry/rip_compname.txt` — NEW — verbatim sample of `rip.pl -r SYSTEM -p compname` output (one short text block, ~10 lines).
- `tests/fixtures/registry/rip_plugins_list.txt` — NEW — verbatim trimmed `rip.pl -l` output (one plugin per line; ≥10 plugins covering compname, userassist, shellbags, usbstor, run, appcompatcache, bam, services, timezone, currentversion).
- `tests/integration/tools/test_registry_regripper_integration.py` — NEW — skipif-guarded test invoking the real `/usr/local/bin/rip.pl` against a tiny SYSTEM hive fixture.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered SYSTEM hive at /evidence/case-001/SYSTEM
And the evidence registry contains its SHA256
And plugin_name == "compname"
When regripper_run is called with RegripperInput(hive_path=Path(".../SYSTEM"), plugin_name="compname")
Then ResponseEnvelope.success == True
And data is RegripperOutput
And data.output_text contains the parsed text emitted by rip.pl on stdout
And data.plugin_name == "compname"
And data.line_count == count of non-empty stdout lines
And data_provenance.tool == "regripper_run"
And data_provenance.cmd_argv == ["/usr/local/bin/rip.pl", "-r", "<hive_path>", "-p", "compname"]
And data_provenance.result_sha256 is the SHA256 of the normalized stdout (per architecture §4.6)
And data_provenance.stdout_path points at cases/<case_id>/audit/blobs/<audit_id>.txt
And the audit JSONL line at cases/<case_id>/audit/registry.jsonl records the plugin invocation with tool="regripper_run", params.plugin_name="compname"
And caveats includes "RegRipper output is structured text — values must be cited as verbatim lines from the stored blob, not paraphrased"
And caveats includes "RegRipper3.0 replays dirty hive transaction logs (.LOG1/.LOG2); older RegRipper 2.x does not — confirm rip.pl version if a Run-key value seems missing"
And caveats includes "Registry LastWriteTime is per-key, not per-value — a key's LastWriteTime tells you SOME value changed at that time, not which one"

Given a registered hive but plugin_name == "totally_made_up_plugin"
When regripper_run is called
Then ResponseEnvelope.success == False
And ResponseEnvelope.advisories[0] contains "PLUGIN_NOT_FOUND: totally_made_up_plugin"
And advisories suggests calling rip.pl -l (or a known-plugin allowlist) to enumerate valid plugins
And no rip.pl subprocess is spawned for the unknown plugin

Given an unregistered hive path /evidence/case-001/SYSTEM_HALLUCINATED
When regripper_run is called
Then ResponseEnvelope.success == False
And ResponseEnvelope.advisories[0] contains "EVIDENCE_NOT_REGISTERED"
And no rip.pl subprocess is spawned

Given /evidence/ is mounted without ro,noexec,nosuid
When regripper_run is called
Then ResponseEnvelope.success == False
And advisories[0] contains "MOUNT_NOT_RO_NOEXEC_NOSUID"

Given a registered hive whose on-disk SHA256 no longer matches the manifest (tampered post-registration)
When regripper_run is called
Then ResponseEnvelope.success == False
And advisories[0] contains "EVIDENCE_HASH_MISMATCH"

Given a registered hive file that is NOT a valid registry hive (truncated / wrong magic)
When regripper_run is called with a known plugin
Then ResponseEnvelope.success == False
And advisories[0] contains "PARSE_FAILED" with the rip.pl stderr substring captured
And data.line_count == 0
And the audit log records the invocation + the failure

Given rip.pl is missing from /usr/local/bin/rip.pl
When regripper_run is called
Then ResponseEnvelope.success == False
And advisories[0] contains "REGRIPPER_NOT_INSTALLED — RegRipper3.0 expected at /usr/local/bin/rip.pl per SIFT 2026 saltstack"
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/tools/test_registry_regripper.py -v
# Must show ≥6 passing

# Integration (skipped if rip.pl missing)
uv run pytest tests/integration/tools/test_registry_regripper_integration.py -v

# Lint + format + types
uv run ruff check src/silentwitness_mcp/tools/registry.py tests/unit/tools/test_registry_regripper.py
uv run ruff format --check src/silentwitness_mcp/tools/registry.py
uv run mypy --strict src/silentwitness_mcp/tools/registry.py

# Single-tool file LOC budget holds (≤200)
wc -l src/silentwitness_mcp/tools/registry.py | awk '{ if ($1 > 200) exit 1 }'

# §14 clean
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **RegRipper path (verified — `context/.raw-design-research/03` line 95).** `rip.pl` is symlinked at `/usr/local/bin/rip.pl`. Plugins live at `/usr/share/regripper/plugins/`. RegRipper3.0 is the active fork (not RegRipper 2.x — they have plugin-compatibility differences per `context/domain/06` §6.1 line 1501). Always call `/usr/local/bin/rip.pl` — never bare `rip.pl` (PATH may vary in subprocess env).
- **Invocation pattern.** `/usr/local/bin/rip.pl -r <hive_path> -p <plugin_name>`. Plugin output goes to stdout as plain structured text (NOT JSON, NOT CSV). The full canonical example list lives at `context/domain/06` §6.1 lines 1460–1468.
- **Plugin enumeration.** Run `rip.pl -l` once at process startup and cache the parsed plugin names in a module-level `set[str]` via `functools.lru_cache(maxsize=1)`. Re-run on `RegripperOutput` cache miss. Use this set to validate `plugin_name` BEFORE spawning the per-call subprocess — the `PLUGIN_NOT_FOUND` advisory must not incur a real rip.pl invocation cost.
- **`parsed_keys` extraction.** RegRipper plugins follow a loose convention of emitting `Key path: HKLM\…\KeyName` and `LastWrite: <ISO timestamp>` lines. Extract every `Key path:` (or `Key:`) line value into `RegripperOutput.parsed_keys` for downstream cross-reference. Do NOT try to parse the values themselves — the text remains the authoritative source. Plugins emit varying shapes; conservative extraction (regex on `^\s*(?:Key|Key path):\s+(.+)$`) is sufficient.
- **Stdout is the structured-text result.** Capture stdout into `output_text` directly. Normalize per architecture §4.6 (strip ANSI, `\r\n` → `\n`, collapse trailing whitespace) BEFORE computing `result_sha256` and writing to `cases/<case_id>/audit/blobs/<audit_id>.txt`. The full normalized blob — not a truncated summary — is what the citation gate will later verify spans against.
- **Caveat strings — verbatim.** Use the three caveat strings above exactly. The "structured text — verbatim lines, not paraphrased" caveat is the most important: it tells the agent that subsequent `record_observation` calls must cite specific lines from the blob via `CitedSpan(line_start, line_end, span_text)` — the citation gate's `SPAN_NOT_IN_LINES` rejection fires hard on paraphrased registry values.
- **Dirty hive log replay.** Per `context/domain/06` §6.1 line 1578: RegRipper3.0 handles dirty hives + .LOG1/.LOG2 replay; RegRipper 2.x does not. The caveat above warns the agent of mysterious "missing Run key value" outcomes — this prevents the model from forming a false negative when log replay would have surfaced the value.
- **Key vs value LastWriteTime.** Per `context/domain/06` line 1580: only the key has a LastWriteTime; individual values do not. The third caveat prevents the agent from claiming "the value Y was written at time T" — it cannot know that from registry timestamps alone.
- **Audit logging is family=registry.** `cases/<case_id>/audit/registry.jsonl` per architecture §4.4. The `tool` field in the JSONL line is `"regripper_run"`.
- **Plugin allowlist or not?** MVP: validate the plugin name exists via cached `rip.pl -l` output (accepts any plugin RegRipper3.0 ships with). Do NOT hardcode a curated plugin list — that's a downstream story (`regripper_curated_pivots` if needed). The architecture intent is "every registry plugin is a typed call"; the typing comes from the input/output models, not from plugin name restriction.
- **Single-tool file.** `tools/registry.py` is separate from `tools/disk.py` (no shared module — different family per architecture §4.4 audit channel). Budget ≤200 LOC. Resist the temptation to add `regripper_batch` or `regripper_run_with_followups` in this story — keep it one tool.
- **Vocab discipline.** No "court-admissible," no "Ralph Wiggum." Use "structured text," "verbatim citation," "key-level timestamp" — the precise registry vocabulary from encyclopedia §15.
