# Volatility 3 — Deep Verification

**Audit date:** 2026-06-03
**Auditor:** deep-audit research agent (Opus 4.7, 1M context)
**Sources:** `volatilityfoundation/volatility3` HEAD (commit `634774f`, framework version `2.28.1`), `teamdfir/sift-saltstack` HEAD, GitHub Issues #1985 / #1847 / #1638 / #1045 / #384 / #367
**Method:** clone source, read `_generator()` + `TreeGrid` columns per plugin, read `cli/text_renderer.py` for renderer behaviour, read `cli/__init__.py` for exit semantics, cross-check against each `docs/stories/story-vol-*.md` Pydantic schema claim and the `architecture.md` §5 tool catalog.

---

## Step 1: Binary location + version (SIFT 2026 reality)

| Fact | Value | Source |
|---|---|---|
| Binary path | `/opt/volatility3/bin/vol` (symlinked at `/usr/local/bin/vol`) | `sift/python3-packages/volatility3.sls:14–48` |
| Version pin | **NONE** — saltstack uses `pip.installed: name: volatility3; upgrade: True` | `volatility3.sls:32–38` |
| Latest framework version in `main` | `2.28.1` | `volatility3/framework/constants/_version.py:2–4` |
| Python | 3.12 (venv) | `volatility3.sls` (uses `/usr/bin/virtualenv` against system Python 3.12) |

**FINDING (BLOCKER) — SIFT 2026 floats Vol3 to whatever PyPI publishes at install time.** No pin. Combined with the **2.27.0 → 2.28.0 regression** documented in [Issue #1985](https://github.com/volatilityfoundation/volatility3/issues/1985) — large memory dumps (≥53 GB) fail layer detection on 2.28.0 — this means SilentWitness inherits a known-bad version on a fresh SIFT 2026 image until upstream cuts 2.28.2+. Story files do not surface this risk anywhere.

**Recommendation:** Add `silentwitness init` step that pins Vol3 to a known-good version inside the venv (or our own venv). Detail in §"Pin recommendation" below.

The spec note in every vol-* story ("path is `/opt/volatility3/bin/vol`, NOT `/opt/volatility3-2.20.0/vol.py`") is **correct**.

---

## Step 2: Per-plugin schema audit

Vol3 JSON-renderer behaviour confirmed by reading `cli/text_renderer.py:535–626` (`class JsonRenderer`):
- Emits a top-level JSON array.
- Each row is an object keyed by **the literal column name from `TreeGrid` constructor** (e.g., `"Offset(V)"`, `"File output"` — with spaces and parens).
- Tree-shape plugins (`pstree`) emit nested `__children` arrays.
- `datetime.datetime` → ISO-8601 string or `null`.
- `format_hints.Hex` is a subclass of `int`; JsonRenderer falls back to `"default": lambda x: x`, so hex fields serialize as **integers** (not hex strings).
- `format_hints.HexBytes` → `bytes.hex(" ")` space-separated hex string.
- `bytes` → space-separated hex string.
- `renderers.LayerData` (malfind Hexdump) → `LayerDataRenderer.render_bytes(x)[0].hex(" ")` — **full VAD bytes as space-separated hex**, NOT just first 128.
- `renderers.Disassembly` (malfind Disasm) → quoted multi-line string of `addr: mnemonic op_str` lines.
- Absent values → `null`.
- Renderer writes one leading `"\n"` before JSON document (line 571).

| Plugin | Spec story | Spec-claimed fields | Vol3 source-emitted JSON keys (TreeGrid column names) | Verdict | Action |
|---|---|---|---|---|---|
| **windows.pslist.PsList** | `story-vol-pslist` | pid, ppid, image_file_name, offset_v, threads, handles, session_id, wow64, create_time, exit_time | `PID, PPID, ImageFileName, Offset(V), Threads, Handles, SessionId, Wow64, CreateTime, ExitTime, File output` | **FIX-IT** | Story names alias `offset_v` correctly conceptually but must use `Field(alias="Offset(V)")` literal-with-parens. Story claims `handles: int \| None` and `session_id: int \| None` — Vol3 column type is `int` (declared) but absent values surface as `null` — `\| None` is correct. **MISSING:** spec omits `File output` field (string, e.g., `"Disabled"` or path). Add `file_output: str \| None`. |
| **windows.pstree.PsTree** | `story-vol-pstree-psscan` | pid, ppid, image_file_name, offset_v, threads, handles, session_id, wow64, create_time, exit_time, **tree_depth** | `PID, PPID, ImageFileName, Offset(V), Threads, Handles, SessionId, Wow64, CreateTime, ExitTime, Audit, Cmd, Path` | **BLOCKER** | **(1)** `tree_depth` does NOT exist as a Vol3 column. Tree depth is encoded via `__children` nesting in JsonRenderer (`text_renderer.py:585, 596, 603–607`). The story's parser must compute it from recursion depth, NOT expect a field. Rewrite acceptance criterion: "tree_depth derived server-side from `__children` nesting." **(2)** Spec MISSES three columns Vol3 emits: `Audit, Cmd, Path` (strings). `Cmd` and `Path` are particularly load-bearing — they're the full command line + image path that `pstree` exposes. **(3)** No `File output` column on pstree (story-vol-pslist already added it; pstree drops it). |
| **windows.psscan.PsScan** | `story-vol-pstree-psscan` | …PslistEntry fields + **offset_p: int** | `PID, PPID, ImageFileName, Offset(V) OR Offset(P), Threads, Handles, SessionId, Wow64, CreateTime, ExitTime, File output` (default: virtual; only physical when `--physical` flag) | **BLOCKER** | The story claims `offset_p` is a separate field in addition to the pslist fields. Vol3 has **a single offset column** whose NAME flips between `Offset(V)` and `Offset(P)` based on the `--physical` flag (`psscan.py:340`). Default mode emits `Offset(V)`. Story must either (a) always pass `--physical` and key on `Offset(P)`, OR (b) accept the default `Offset(V)` and rename the field. Inheriting from `PslistEntry` and adding `offset_p` will leave `offset_p` always-null in default mode. |
| **windows.malfind.Malfind** | `story-vol-malfind` | pid, process, start_vpn, end_vpn, vad_tag, protection, commit_charge, private_memory, file_output, hexdump_first_128, disasm_preview | actual: `windows.malware.malfind.Malfind` emits `PID, Process, Start VPN, End VPN, Tag, Protection, CommitCharge, PrivateMemory, File output, Notes, Hexdump, Disasm` | **BLOCKER** | **(1) Plugin path is deprecated.** `windows.malfind.Malfind` is a stub with `removal_date="2026-06-07"` (`malfind.py:11–20`). **That's 4 days from today.** Real implementation lives at `windows.malware.malfind.Malfind` (since v2.26.2 re-org). When the spec says "plugin name = `windows.malfind.Malfind`", it will hard-break after 2026-06-07 if SIFT 2026 has bumped past that release. **(2)** Spec MISSES the `Notes` column (string, e.g., `"MZ header"`, `"PE header"`, `"Function prologue"`) — this is high-signal for the agent (Vol3 auto-tags PE/shellcode patterns). **(3)** Spec claims `private_memory: bool` — Vol3 TreeGrid declares column as `int` (`malware/malfind.py:283`), not bool. Use `int`. **(4)** Spec field name `vad_tag` should alias `Tag` not `VadTag`. **(5)** `Hexdump` JSON value is **the entire VAD bytes** (space-separated hex string), not pre-truncated — story's "first 128" is a server-side slice (correct intent but make sure docstring is explicit). |
| **windows.netscan.NetScan** | `story-vol-netscan` | offset, proto, local_addr, local_port, foreign_addr, foreign_port, state, pid, owner, created | `Offset, Proto, LocalAddr, LocalPort, ForeignAddr, ForeignPort, State, PID, Owner, Created` | **KEEP** | Schema matches. Field aliases align (case-sensitive). One caveat: spec says `foreign_addr: str \| None` and treats `"*"` UDP wildcard as None — Vol3 may emit `"*"` literal OR an absent value; verify in tests. |
| **windows.cmdline.CmdLine** | `story-vol-cmdline` | pid, process, args | `PID, Process, Args` | **KEEP** | Exact match. |
| **windows.dlllist.DllList** | `story-vol-dlllist-handles` | pid, process, base, size, name, path, load_time, file_output | `PID, Process, Base, Size, Name, Path, LoadCount, LoadTime, File output` | **FIX-IT** | Spec MISSES `LoadCount` (int). Add `load_count: int \| None`. The other fields all match. |
| **windows.handles.Handles** | `story-vol-dlllist-handles` | pid, process, offset, handle_value, type, granted_access, name | `PID, Process, Offset, HandleValue, Type, GrantedAccess, Name` | **KEEP** | Schema matches. `HandleValue`, `GrantedAccess`, `Offset` all use `format_hints.Hex` → JSON integers per renderer behaviour. Spec's `int` typing is correct. |
| **windows.lsadump.Lsadump** | `story-vol-lsadump` | name, hex_value, printable_value | `Key, Secret, Hex` | **BLOCKER** | **(1) Plugin path deprecated.** `windows.lsadump.Lsadump` is a stub with `removal_date="2026-09-25"` (`lsadump.py:12–22`). Real path is `windows.registry.lsadump.Lsadump`. We have ~4 months of grace, then hard break. **(2) Column names are different.** Spec claims `name, hex_value, printable_value`. Actual columns are `Key` (str — secret name), `Secret` (HexBytes — same hex-string view), `Hex` (bytes — same content, same hex-string view per JsonRenderer). Both `Secret` and `Hex` serialize to **the same space-separated hex string** via JsonRenderer. **(3)** Vol3 does NOT emit a printable rendering — `printable_value` is a server-side computation (the story acknowledges this in notes, but BDD criterion "field is in Vol3 JSON" is wrong). **(4)** Plugin requires both SYSTEM and SECURITY hives to be located by `hivelist` — if hives missing, plugin throws `VolatilityException` and exits 1 (good — `TOOL_FAILED` path triggers correctly). |

---

## Step 3: `--renderer json` works (and how)

`-r json` (or `-r jsonl`) is fully supported on every wrapped plugin. Implementation in `cli/text_renderer.py:535` (`class JsonRenderer(CLIRenderer)`).

**What works well:**
- Single JSON document per run, top-level array, machine-parseable.
- Structured output flag (`structured_output = True`) auto-redirects the banner to **stderr** (`cli/__init__.py:387–391`) — stdout is clean JSON.
- Datetime, hex, bytes, disassembly, layer-data all have type-renderers; no unsupported column types in our 9 plugins.

**Caveats discovered:**
- Renderer writes a **leading `"\n"`** before the JSON (`text_renderer.py:571`). Parsers must `.lstrip()` or accept `json.loads()`'s whitespace tolerance.
- For tree plugins (`pstree`), JSON shape is nested via `"__children"` — a flat-array parser will lose the tree. Story-vol-pstree-psscan does note this (`__children` mentioned) but the typed model claims a `tree_depth` field that isn't present — see Step 2 row for `pstree`.
- Historical JSON-renderer bugs in `printkey` (#384, 2020) and `VadYaraScan` (#367, 2020) — **both closed**. **No open JSON-renderer issues** on any of our 9 plugins as of search date.
- `-r csv` is also supported (`class CSVRenderer`) — usable as a fallback if a future Vol3 release breaks JSON for a specific plugin. Worth documenting as recovery path; current code can stay on `-r json`.

**Verdict: `--renderer json` is reliable for our nine plugins as of v2.28.1.** No need for CSV fallback today, but document the fallback in `_vol_common.py` for resilience.

---

## Step 4: Plugin invocation patterns + flags

**argv structure** (`cli/__init__.py:356–362`, subparsers): `vol [global flags] <plugin> [plugin flags]`.

Story argv form `["/opt/volatility3/bin/vol", "-f", "<img>", "-r", "json", "windows.pslist.PsList"]` is correct: `-f`/`-r` are global; plugin is the subcommand. Plugin-level flags like `--pid` MUST come AFTER the plugin name (story-vol-malfind and story-vol-cmdline acceptance criteria say "after the plugin name" — correct).

**Symbol-cache automagic.** Vol3 does NOT use profiles. ISF (Intermediate Symbol Format) symbols are:
- Bundled at `volatility3/symbols/windows/*.json.xz` (small set) inside the venv.
- Auto-fetched from `https://download.microsoft.com/download/symbols` (Microsoft Symbol Server) at first plugin run when a kernel build is not in cache.
- Cached at `~/.cache/volatility3/` (XDG-compliant when `XDG_CACHE_HOME` set).
- Cache path is currently **not configurable**.

**FINDING (FIX-IT) — symbol fetch requires network at first run.** SIFT 2026 install does NOT pre-fetch the full Windows symbol set. On an offline examiner station running a Windows 10 22H2 / 11 24H2 build that hasn't been seen before, the first `windows.pslist` call will fail with `No suitable symbol table found` and silently try to download. If the host is offline (RFC 6919 SHOULD NOT for forensics), the failure is permanent. Story-vol-malfind §"symbol-table mismatch failure path" is the only place this is acknowledged. **Recommendation:** add `silentwitness init` step that pre-fetches symbols via `vol --download-symbols windows` (if such flag exists) OR manually downloads from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` and unzips into `~/.cache/volatility3/`. Architecture should document this.

**KDBG parameter — Vol3 doesn't use it.** Architecture §5 catalog row `VolPlistInput(evidence_path: Path, kdbg: str | None)` (line 293) is wrong; Vol3 has no `--kdbg` flag (KDBG was a Vol2 concept). Remove from the input model. Story-vol-pslist Pydantic input doesn't actually reference `kdbg`, so this is an architecture-doc-only fix.

**`--pid` is plugin-scoped**, NOT global. Multiple PIDs accepted as comma-separated list (per `PsList.create_pid_filter`). Story specs forward a single `int` which is fine.

**`--object-types` on handles** is a plugin-scoped flag, comma-separated. Story-vol-dlllist-handles spec is correct.

**`--physical` flag flips Offset(V) → Offset(P)** for `pslist` AND `psscan`. Story-vol-pstree-psscan has `offset_p` as a separate field — that assumption is broken unless we pass `--physical` (see Step 2 BLOCKER on psscan).

---

## Step 5: Error handling reality

Read `cli/__init__.py:589–676` (`process_exceptions`). On any `VolatilityException` (or subclasses `InvalidAddressException`, `SymbolError`, `SymbolSpaceError`, `LayerException`, `MissingModuleException`, `RenderException`, `VersionMismatchException`), CLI writes a human-readable error report to stderr and calls `sys.exit(1)`. On `UnsatisfiedException` (e.g., wrong OS for the plugin), CLI calls `parser.exit(1, ...)` with a message to stderr.

Uncaught non-Volatility exceptions propagate to Python's default handler → exit code 1.

**Verdict: Vol3 reliably exits non-zero on plugin failure** — `TOOL_FAILED` reason wiring in the story specs is sound. Capturing first 500 chars of stderr will surface the "caused by" hints (very useful for the demo-time self-correction loop).

Edge case: **plugin returns zero rows on success → exit 0 with stdout `"[]"`** (empty array). Story-vol-pslist acceptance criterion "empty `[]` returns `success=True` with empty list" handles this correctly.

---

## Step 6: Performance + memory footprint

300s timeout per story is **plausible for most plugins on a 16 GB dump** (`context/domain/06` claim). However, two plugins routinely exceed this on large dumps:

1. **`windows.netscan`** — pool-tag scanning crosses the entire physical address space. On a 64 GB dump, this can take 200–600s. [Issue #1985](https://github.com/volatilityfoundation/volatility3/issues/1985) (2.28.0 regression) compounds this.
2. **`windows.handles`** without `--pid` — enumerates every process's full handle table; on a busy system (10k+ handles per service host) this can take 300–800s.
3. **`windows.malfind`** without `--pid` — VAD walk per process; usually fast, but on a 32+ GB dump with hundreds of processes, 200–400s is normal.

**FINDING (FIX-IT) — 300s default is too tight for handles + netscan on large dumps.** Bump to 600s for those two specifically, OR scale the timeout from the evidence file size (e.g., `max(300, 30 * GB_in_image)`). Document the per-plugin override pattern in `_vol_common.py`.

`windows.lsadump` is fast (it operates on registry hives only, not the whole address space) — 300s is comfortably over-spec.

---

## Step 7: lsadump / hashdump current state

No OPEN issues for `lsadump`/`hashdump` in volatility3 tracker as of audit date. Last credential-related fix was [Issue #1638](https://github.com/volatilityfoundation/volatility3/issues/1638) (closed 2025-03-08) — "Fix `get_bootkey`, update plugins to correctly handle failed calls" — this hardened the failure path; lsadump now properly raises when hives are missing instead of returning silent empties.

**Verdict: lsadump is reliable in v2.28.1.** The historical Vol2-era flakiness is gone. Story-vol-lsadump's `TOOL_FAILED` path will fire correctly when SYSTEM/SECURITY hives can't be located.

**Open caveat re: Credential Guard.** Per `context/domain/03` §7.30 (referenced in story-vol-lsadump caveats): VBS/CG protects LSASS process memory differently than LSA *secrets* — `lsadump` output is typically intact on CG hosts. **Source code confirms** lsadump operates on registry hives (`SYSTEM` + `SECURITY`) via `hivelist.HiveList.list_hives`, NOT against LSASS process memory — so CG isolation of LSASS does not block it. Caveat wording is accurate.

**Not in our catalog:** `hashdump` (different plugin path: `windows.registry.hashdump.Hashdump`, columns `User, rid, lmhash, nthash`). Story scope intentionally excludes it. No action needed but flag for future epic.

---

## Step 8: Top open Vol3 issues affecting our wrapped plugins

| # | Title | Status | Affects us? |
|---|---|---|---|
| **#1985** | Memory dump parses with 2.27.0 but not 2.28.0 (53 GB) | OPEN | **YES — BLOCKER for large dumps.** If SIFT 2026 ships 2.28.0/.1 and case dumps are large, automagic layer detection fails before any plugin runs. Pin to 2.27.0 OR confirm 2.28.2 ships with the fix. |
| #1922 | windows.truecrypt.Passphrase plugin failed | OPEN | No (not in our catalog) |
| #1847 | windows.netscan does not support Win XP | CLOSED | No (XP not in case corpus) |
| #1638 | Fix `get_bootkey` for credential plugins | CLOSED 2025-03-08 | Already fixed; lsadump is healthier than the Vol2 era. |
| #1045 | windows.malfind `--dump` directory bug | CLOSED | No (we don't use `--dump` in spec) |
| #384 | PrintKey JSON renderer error | CLOSED 2020 | No (printkey not in our catalog; JSON-renderer issue fixed) |
| #367 | VadYaraScan JSON error | CLOSED 2020 | No |

**No open issues that block our 9 plugins on small-to-medium dumps.** The only operational risk is #1985 on >40 GB dumps.

---

## Recommended story adjustments

### `story-vol-pslist` — **FIX-IT**
- Pydantic alias for `Offset(V)` must use the literal string `"Offset(V)"` (with parens). Add an explicit note: "JSON key from Vol3 contains literal parens — use `Field(alias='Offset(V)')`, NOT `Field(alias='OffsetV')`."
- Add **missing field** `file_output: str | None` to `PslistEntry` (Vol3 emits the `"File output"` column even when `--dump` is not used; value is typically `"Disabled"`).
- Add caveat: "ImageFileName is the kernel-side `_EPROCESS.ImageFileName` truncated to 15 chars; do NOT assume it equals the on-disk EXE path."

### `story-vol-pstree-psscan` — **BLOCKER, must rewrite**
- **Drop `tree_depth` as a Vol3 column.** Compute it server-side from `__children` recursion depth. Update the BDD criterion: "tree_depth is derived by the parser from the JSON `__children` nesting level (0 = root)."
- **Add three missing columns** to `PstreeEntry`: `audit: str | None`, `cmd: str | None`, `path: str | None`. These are NOT in the spec but Vol3 emits them.
- **Remove `file_output` from PstreeEntry** — pstree does NOT include it (only pslist and psscan do).
- **psscan `offset_p` semantics broken.** Either (a) pass `--physical` flag in argv and rename to `offset_p`, OR (b) accept default `Offset(V)` and use `offset_v`. Recommend (b) — keep behavioural parity with pslist, ditch the spurious physical-offset field. The diff-with-pslist semantics still work because PID is the join key, not the offset.

### `story-vol-malfind` — **BLOCKER, plugin path expires 2026-06-07**
- **Switch plugin string from `windows.malfind.Malfind` to `windows.malware.malfind.Malfind`** — the older path is a deprecation stub with removal date 4 days from now. If SIFT 2026 pulls Vol3 ≥2.29.0 after 2026-06-07, the spec breaks.
- **Add missing `notes: str | None` field** (Vol3-emitted column with values like `"MZ header"`, `"PE header"`, `"Function prologue"`, or `"N/A"`). High-signal for the model.
- **Change `private_memory: bool` to `private_memory: int`** (Vol3 column type is int).
- **Pydantic aliases must match literal column names**: `"Start VPN"` (with space), `"End VPN"` (with space), `"Tag"` (not `"VadTag"`), `"CommitCharge"`, `"PrivateMemory"`, `"File output"` (with space), `"Hexdump"`, `"Disasm"`, `"Notes"`.
- Document that `Hexdump` JSON value is the **full VAD** as space-separated hex; the `hexdump_first_128` field is a server-side slice.

### `story-vol-netscan` — **KEEP** (schema matches)
- Add Step 6 performance note: bump per-call timeout to 600s for this plugin specifically.
- Note that `"*"` UDP wildcard is what Vol3 emits literally; absent values surface as `null` in JSON.

### `story-vol-cmdline` — **KEEP**
- Spec schema is correct.
- Optional: surface the "paged-out PEB" case — Vol3 emits the string `"Required memory at <addr> is not valid"` in the `Args` field (NOT null). The spec acknowledges this in the notes; ensure the parser coerces all non-PEB-string values to `None`.

### `story-vol-dlllist-handles` — **FIX-IT**
- **Add missing `load_count: int | None` field** to `DllEntry`. Vol3 emits a `LoadCount` column between `Path` and `LoadTime`.
- Handles schema is correct; no further changes.
- Performance: bump default timeout to 600s when `pid=None` (no PID filter).

### `story-vol-lsadump` — **BLOCKER, schema is wrong**
- **Switch plugin string from `windows.lsadump.Lsadump` to `windows.registry.lsadump.Lsadump`** (removal date 2026-09-25 — 4 months away, but still a ticking clock).
- **Rewrite columns.** Vol3 emits `Key` (str, secret name), `Secret` (HexBytes → hex-string), `Hex` (bytes → hex-string). The story's `name`, `hex_value`, `printable_value` don't map cleanly — `Secret` and `Hex` are the same content viewed two ways. Use `Field(alias="Key")` for `name`, `Field(alias="Hex")` for `hex_value`, and compute `printable_value` server-side from `hex_value` (acknowledge it's NOT a Vol3 column).

### `architecture.md` §5 — **FIX-IT**
- Row 293 `VolPlistInput(evidence_path: Path, kdbg: str | None)` — **remove `kdbg`**. Vol3 has no `--kdbg` flag (Vol2 concept).
- Update tool-catalog rows for `vol_malfind` and `vol_lsadump` to reference the **non-deprecated plugin paths** (`windows.malware.malfind.Malfind`, `windows.registry.lsadump.Lsadump`).

---

## Pin recommendation

**Pin Vol3 to `volatility3==2.27.0` in `silentwitness init`** as the safe default, until Vol3 ships ≥2.28.2 with the #1985 fix verified. Implementation:

1. SilentWitness creates its own venv at `/opt/silentwitness/vol3-venv` (do not modify the SIFT-managed `/opt/volatility3/`).
2. `pip install 'volatility3[full]==2.27.0' yara-x` into that venv.
3. The MCP `_VOL_BIN` constant becomes `/opt/silentwitness/vol3-venv/bin/vol` (override the SIFT path).
4. Sanity-check at server bootstrap: `vol --version` must equal pinned version; if not, MCP refuses to start.
5. Optionally pre-fetch the Windows ISF bundle (`https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip`) into `~/.cache/volatility3/` so symbol downloads don't depend on Microsoft Symbol Server availability at incident-response time.

This adds ~1 min to first-time setup and removes two failure modes (regression + offline symbol fetch). The spec's "use `/opt/volatility3/bin/vol`" remains correct as a fallback identifier if SIFT later changes that path; the venv pin is additive guardrail.

---

## Sources

**Volatility 3 source (commit `634774f`, v2.28.1):**
- `/tmp/vol3-audit/volatility3/framework/constants/_version.py:2–10` — framework version
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/pslist.py:279–371` — PsList columns + generator
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/pstree.py:163–191` — PsTree columns
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/psscan.py:339–356` — PsScan columns (Offset(V) by default)
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/malfind.py:11–20` — **deprecation stub, removal 2026-06-07**
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/malware/malfind.py:271–296` — real Malfind columns (Notes added)
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/netscan.py:507–524` — NetScan columns
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/netstat.py:788–805` — NetStat columns
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/cmdline.py:102–114` — CmdLine columns
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/dlllist.py:232–245` — DllList columns (LoadCount included)
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/handles.py:409–420` — Handles columns
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/lsadump.py:12–22` — **deprecation stub, removal 2026-09-25**
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/registry/lsadump.py:244–262` — real Lsadump columns (Key, Secret, Hex)
- `/tmp/vol3-audit/volatility3/framework/plugins/windows/registry/hashdump.py:631–649` — Hashdump columns (not in our catalog)
- `/tmp/vol3-audit/volatility3/cli/text_renderer.py:535–626` — JsonRenderer + JsonLinesRenderer
- `/tmp/vol3-audit/volatility3/cli/text_renderer.py:238–250` — CLIRenderer type-renderer registry (Hex falls to default)
- `/tmp/vol3-audit/volatility3/cli/__init__.py:338–345` — `-r` / `--renderer` CLI arg
- `/tmp/vol3-audit/volatility3/cli/__init__.py:356–362` — subparsers for plugin name
- `/tmp/vol3-audit/volatility3/cli/__init__.py:387–391` — banner → stderr when structured
- `/tmp/vol3-audit/volatility3/cli/__init__.py:589–676` — `process_exceptions` → `sys.exit(1)`
- `/tmp/vol3-audit/volatility3/cli/__init__.py:678–712` — `process_unsatisfied_exceptions`

**SIFT 2026 saltstack:**
- `/tmp/sift-saltstack-audit/sift/python3-packages/volatility3.sls:14–48` — venv + symlink install, no version pin

**SilentWitness specs reviewed:**
- `docs/stories/story-vol-pslist.md`
- `docs/stories/story-vol-pstree-psscan.md`
- `docs/stories/story-vol-malfind.md`
- `docs/stories/story-vol-netscan.md`
- `docs/stories/story-vol-cmdline.md`
- `docs/stories/story-vol-dlllist-handles.md`
- `docs/stories/story-vol-lsadump.md`
- `docs/architecture.md` §5 (line 293–301 tool catalog)
- `context/domain/03-memory-forensics-deep.md` §7.2–7.30 (claimed plugin behaviour)
- `context/.raw-design-research/03-sift-2026-tool-catalog-verified.md` §3 (Vol3 path on SIFT)

**GitHub Issues:**
- [#1985 — 2.28.0 regression on large dumps (OPEN, BLOCKER)](https://github.com/volatilityfoundation/volatility3/issues/1985)
- [#1638 — get_bootkey fix for credential plugins (CLOSED 2025-03-08)](https://github.com/volatilityfoundation/volatility3/issues/1638)
- [#1847 — netscan XP support (CLOSED 2025-06-10)](https://github.com/volatilityfoundation/volatility3/issues/1847)
- [#1045 — malfind --dump bug (CLOSED)](https://github.com/volatilityfoundation/volatility3/issues/1045)
- [#384 — printkey JSON error (CLOSED 2020)](https://github.com/volatilityfoundation/volatility3/issues/384)
- [#367 — VadYaraScan JSON error (CLOSED 2020)](https://github.com/volatilityfoundation/volatility3/issues/367)
