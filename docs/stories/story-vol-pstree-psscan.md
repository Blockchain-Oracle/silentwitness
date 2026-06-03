# Story — Vol3 windows.pstree + windows.psscan tool wrappers

**ID:** story-vol-pstree-psscan
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-vol-pslist (provides `_run_vol`, `_VolResult`, `_VOL_CAVEATS`, audit-blob writer)
**Estimate:** ~1h (two wrappers, both formulaic over the skeleton from story-vol-pslist)
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.pstree` (hierarchy view) and `windows.psscan` (pool-tag scan for hidden/terminated processes) as typed MCP tools
**So that** the investigator agent can both visualise lineage AND detect DKOM-hidden processes by diffing `psscan` against `pslist` — the canonical rootkit-detection move (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Autonomous Execution Quality — the diff is what the critic uses to challenge "process X is active").

---

## File modification map

- `src/silentwitness_mcp/tools/memory.py` — UPDATE — add `vol_pstree(...)` and `vol_psscan(...)` async functions; add `PstreeEntry` + `PstreeOutput` + `PsscanEntry` + `PsscanOutput` Pydantic models; extend `_VOL_CAVEATS` with `"pstree"` and `"psscan"` entries. ~70 LOC added (target ≤190 LOC total).
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_pstree` and `vol_psscan` with FastMCP.
- `tests/unit/test_vol_pstree.py` — NEW — ≥5 behavioural test cases: valid JSON parses, nested `__children` structure flattened correctly with server-side depth computation, empty output, `EVIDENCE_NOT_REGISTERED`, `TOOL_FAILED`.
- `tests/unit/test_vol_psscan.py` — NEW — ≥5 behavioural test cases: valid JSON parses including `offset_v` field (virtual offset), process with `exit_time` populated (terminated-but-pool-resident case), empty output, `EVIDENCE_NOT_REGISTERED`, `EVIDENCE_TAMPERED`.
- `tests/integration/test_memory_e2e.py` — UPDATE — add `test_pstree_against_nist_image` and `test_psscan_against_nist_image` cases (skipped if fixture absent).
- `tests/property/test_pslist_psscan_diff.py` — NEW — one Hypothesis property test asserting "for any synthetic pair of (pslist_pids, psscan_pids), the set difference psscan_pids − pslist_pids is what the agent should treat as hidden-or-terminated candidates" — establishes the diff invariant the critic relies on at demo time 4:00–4:30.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem registered and SHA256-matched
When  vol_pstree is called with evidence_path="/evidence/case-001/memdump.vmem"
Then  the response is ResponseEnvelope with success=True
And   data is a PstreeOutput containing list[PstreeEntry]
And   each PstreeEntry has typed fields: pid: int, ppid: int, image_file_name: str, offset_v: int, threads: int, handles: int | None, session_id: int | None, wow64: bool, create_time: datetime | None, exit_time: datetime | None, audit: str | None, cmd: str | None, path: str | None
And   tree shape is encoded via JsonRenderer.__children nesting in the raw Vol3 output; the parser flattens it server-side and computes depth from recursion (depth NOT a column on PstreeEntry)
And   the audit JSONL entry includes cmd_argv ending in ["windows.pstree.PsTree"]
And   caveats includes "Parent PIDs can refer to dead processes via PID reuse — cross-check CreateTime ordering"
And   caveats includes "Process hollowing produces legitimate-looking lineage with malicious code — vol_pstree alone cannot detect it; corroborate with vol_malfind + ldrmodules"

Given the same registered image
When  vol_psscan is called
Then  the response is ResponseEnvelope with success=True
And   data is a PsscanOutput containing list[PsscanEntry]
And   each PsscanEntry has typed fields matching PslistEntry with offset_v: int (Vol3 emits Offset(V) by default; only Offset(P) if --physical flag passed. Wrapper passes no flag → field is virtual offset.)
And   the audit JSONL entry includes cmd_argv ending in ["windows.psscan.PsScan"]
And   caveats includes "windows.psscan may show terminated processes that pslist no longer sees — entries with ExitTime set are normal teardown artifacts, not malice"
And   caveats includes "diff vs vol_pslist: processes in psscan but NOT in pslist are DKOM-hidden OR terminated; ExitTime distinguishes the two"
And   caveats includes "pool-tag scan can produce false positives from non-process allocations — validate Threads/Handles plausibility before trusting an entry"

Given vol_pstree is called against an unregistered evidence path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no Vol3 subprocess is spawned

Given vol_psscan is called and the registered evidence's current SHA256 does not match the manifest
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"

Given Vol3 exits non-zero on either wrapper
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL records exit_code != 0

Given a Hypothesis-generated pair of integer sets (simulated pslist PIDs, simulated psscan PIDs)
When  the property test runs the documented diff algorithm
Then  the algorithm returns (psscan_set - pslist_set) as "hidden_or_terminated_candidates"
And   for every such PID, if its (synthetic) exit_time is None the agent should treat it as DKOM-hidden candidate; otherwise terminated
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_pstree.py tests/unit/test_vol_psscan.py -v
# Must show ≥10 passing test cases combined

uv run pytest tests/property/test_pslist_psscan_diff.py -v
# Must pass with default Hypothesis settings

uv run pytest tests/integration/test_memory_e2e.py::test_pstree_against_nist_image tests/integration/test_memory_e2e.py::test_psscan_against_nist_image -v
# Must pass when NIST fixture present; SKIPPED otherwise

uv run ruff check src/silentwitness_mcp/tools/memory.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py
# Both exit 0

wc -l src/silentwitness_mcp/tools/memory.py
# Must show ≤400 (target ≤190 after this story)
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **pstree JSON shape.** Vol3 `-r json windows.pstree.PsTree` emits a nested structure with a `__children` key per row. Flatten breadth-first into a flat `list[PstreeEntry]` server-side; tree depth is computed from recursion depth during the flatten pass but is NOT a column on `PstreeEntry`. Tree shape is preserved by the parser-internal traversal; downstream consumers that need depth call a separate `compute_depth(entries)` helper. Verified shape in `context/domain/06` §"renderer json".
- **pstree extra columns.** Per Vol3 ≥2.27.0 schema, `PstreeEntry` MUST include three additional optional columns: `audit: str | None` (PEB audit info), `cmd: str | None` (full pre-process command line — high signal for LOLBin detection), and `path: str | None` (image path). These are emitted by `-r json windows.pstree.PsTree` and dropping them loses signal the malfind/cmdline correlation pass needs.
- **psscan vs pslist columns.** Per `context/domain/03` §7.3: psscan returns the same columns as pslist. Vol3 emits `Offset(V)` by default; only `Offset(P)` is emitted if the `--physical` flag is passed. The wrapper passes no flag → field is virtual offset (`offset_v: int`). Model `PsscanEntry` as inheriting from `PslistEntry` (Pydantic v2 model inheritance) for LOC budget — no additional offset column needed.
- **The killer move — diff semantics.** `context/domain/03` §7.3 — "Processes in psscan but NOT in pslist = hidden OR terminated. Processes in pslist but NOT in psscan = recently created and not yet pool-tagged (rare)." The property test must encode this invariant so the critic agent (Epic 10) can rely on it. `exit_time IS NULL` differentiates DKOM-hidden from terminated.
- **Reuse `_run_vol`.** Both wrappers are 4-liners on top of `_run_vol` from story-vol-pslist — change plugin name + output-model parse. Do NOT duplicate the subprocess scaffolding.
- **Caveats source.** `context/domain/03` §7.3, §7.4. The "may show terminated processes" caveat is load-bearing for the demo — the investigator's pivot at 3:00–3:30 explicitly cites it.
- **Plugin name strings.** `windows.pstree.PsTree` and `windows.psscan.PsScan` — class-suffixed form, future-proof.
- **Subprocess timeout default.** Inherits 300s from `_run_vol`. psscan can be slower than pslist on large images — that is acceptable within 300s for a 16GB dump per `context/domain/06` §"Performance scales with image size".
- **No new caveat catalog file.** Append to the dict in `_vol_common.py`; do NOT create a YAML registry. The architecture commits to in-code per-tool caveats; the YAML approach is only used for the sanitizer pattern catalog.
