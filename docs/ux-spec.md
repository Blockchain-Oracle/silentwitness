# UX Spec — SilentWitness

**Status:** DRAFT
**Last updated:** 2026-06-02
**Primary surface:** CLI (Typer)
**Secondary surface:** optional streaming HUD on `localhost:8088`

> Template adapted: web concerns dropped; CLI-primary. HUD is a stretch renderer over the same data. Sources: `STRATEGY.md`, `docs/BRAINSTORM.md`, `docs/PRD.md`, `context/user/09-ir-consultant-reality.md`, `context/.raw-design-research/03-sift-2026-tool-catalog-verified.md`.

---

## 1. The user this UX is for

Senior IR consultant at a Tier-2 boutique (Aspen, Volexity, Sygnia, TrustedSec IR). 5–15 years, SANS GCFA, terminal-native. Often working over `ssh` into a firm SIFT VM from hotel Wi-Fi. Per `context/user/09 §A`: "laptop within arm's reach 24/7." Per §F.2: command-line stenography is the pain. Per §A.7: hates slow, GUI-bound, click-through-modal tools.

**Worst-case assumption:** SSH over flaky hotel link. No GUI. No JS. The CLI must remain legible when ANSI is stripped (`silentwitness ... | cat` must read). HUD is optional; CLI is source-of-truth.

---

## 2. Surface 1 — CLI (Typer) — the primary surface

### 2.1 Anchor CLIs

Three CLIs whose ergonomics we selectively steal.

| Anchor | What we steal | Why |
|---|---|---|
| **`gh`** | Verb-first noun-second grammar; structured `--json` alongside human default; `--repo`-style scope flag. | IR consultants already know `gh`. `silentwitness investigate <case>` reads the same. |
| **`httpie`** | Color-coded sections by semantic role; generous whitespace; output that reads like a typed page, not a packed log. | Investigation output is heterogeneous (hypotheses, tool calls, observations, pivots). Color-by-role lets the eye skim. §A.7 hates dense output. |
| **`uv`** | Single-binary install; instant first run; readable progress on long ops; never blocks in scripted mode. | An investigation is 5–30 min; the analyst tabs away. Render must stay legible when they tab back. |

Implicit fourth: **`kubectl`** — `--context`-style global scope (we use `--case`) and verb/noun grammar. Not adopted: `ripgrep`/`fd` (too terse for IR), `rich`-only TUIs (over-rich; flaky SSH wants legibility, not animation).

### 2.2 Command catalog

Verb-first, case-scoped. All commands accept `--case <case-id>` if not positional; active case from `$SILENTWITNESS_CASE` if neither given.

Exit-code semantics (uniform):

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | User error (bad flags, missing argument, unknown case) |
| 2 | System error (tool not found, evidence unreadable, MCP server down) |
| 3 | Verification rejection (citation gate or entity gate refused the operation) |
| 4 | Examiner password wrong / approval denied |
| 130 | SIGINT (graceful Ctrl-C; partial state checkpointed) |

#### `silentwitness init <case-id>`

Creates the case skeleton. Idempotent unless `--force`. Flags: `--examiner` (default `$USER`), `--model`, `--force`, `--no-mount` (tests only).

```
$ silentwitness init mr-evil-001
[green]✓[/green] case 'mr-evil-001' initialized at /home/sansforensics/cases/mr-evil-001
       ├─ audit/        (JSONL tool-call ledger)
       ├─ evidence/     (registered symlinks — ro,noexec,nosuid mount)
       ├─ report.md     (DRAFT — frontmatter only)
       └─ .silentwitness/case.toml
```

#### `silentwitness register-evidence <path>`

SHA-256s every file under `<path>` and registers it. Validates `ro,noexec,nosuid` mount per BRAINSTORM Decision 5. Flags: `--label`, `--recursive`, `--dry-run`.

```
$ silentwitness register-evidence /mnt/evidence/SchardtPC.E01 --case mr-evil-001
[green]✓[/green] registered SchardtPC.E01
       sha256: 3a4f...c901    size: 4.2 GiB
       mount:  /mnt/evidence (ro,noexec,nosuid) [green]✓[/green]
```

#### `silentwitness investigate <case-id>`

The primary command. Fires the investigator agent (5–30 min on NIST Hacking Case). Default render: live layout (§2.3). Non-TTY stdout → line-buffered `EVT ` JSONL for `jq`. Flags: `--model`, `--max-steps` (200), `--max-tokens` (800k), `--specialist`, `--resume`, `--hud` (auto-start HUD).

#### `silentwitness status <case-id>`

Snapshot of case state. Reads `audit/hypothesis.jsonl` + in-flight state file. Safe during active runs. Flags: `--json`, `--watch`, `--full`.

```
$ silentwitness status mr-evil-001
case:        mr-evil-001       model:   anthropic:claude-opus-4-7-1m
examiner:    sansforensics     status:  INVESTIGATING (12m 04s elapsed)

hypothesis stack (3 active, 2 confirmed, 1 pivoted, 0 abandoned):
  H-007 [ACTIVE]    wardriving — Ethereal + intercepted SMTP creds
  H-006 [ACTIVE]    Schardt is the user; Documents and Settings\Mr. Evil\
  H-005 [CONFIRMED] memory image OS = WinXP SP2 (vol windows.info)
  H-004 [PIVOTED]   ⤳ vol3 symbol-table mismatch; rebuilt

findings: staged 9  approved 0  rejected 1 (entity gate)
tokens:   312k / 800k budget
last pivot: 12:34:07Z  H-004 → H-005  symbol-table rebuilt
```

#### `silentwitness review <case-id>`

Per Open Question §8: **v1 = plain print + prompt**, no TUI. Lists staged findings; analyst steps through. Flags: `--finding`, `--status`, `--non-interactive`. The plain prompt works over `ssh -tt` on flaky links — the worst case. Textual is post-hackathon.

```
$ silentwitness review mr-evil-001

[1/9] F-mr-evil-001-001  staged 12:18:02Z
─────────────────────────────────────────
observation: "C:\Program Files\Ethereal\ethereal.exe was present on
              Schardt's profile (MFT record dated 2004-08-19 22:48 UTC)."
interpretation: "Ethereal (now Wireshark) is a packet-capture tool;
                 combined with promiscuous-mode capability this is
                 consistent with wardriving."
cited:     sift-001-20260602-014, sift-001-20260602-019
caveats:   "Tool installation alone does not prove use; corroborate
            via captured pcap or memory residue."
mitre:     T1040 (Network Sniffing)

[a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  >
```

#### `silentwitness approve <finding-id>`

Password-gated examiner approval; writes HMAC-signed ledger entry (full flow §2.4). Flags: `--note`, `--ledger`. Exit 4 on wrong password (re-prompt up to 3 then bail).

#### `silentwitness verify <case-id>`

Re-reads HMAC ledger and recomputes signatures over every approved finding's substantive text. Exit 0 if intact; exit 3 if any entry tampered. Flags: `--ledger`, `--strict` (also recompute audit-output SHA256s).

```
$ silentwitness verify mr-evil-001
[green]✓[/green] ledger intact — 14 entries verified
       PBKDF2-SHA256, 600,000 iter
       window: 2026-06-02T12:25:01Z → 13:48:30Z
```

#### `silentwitness export <case-id>`

Render the deliverable. Flags: `--pdf` (WeasyPrint), `--md`, `--include-appendix-audit / --no-appendix-audit`, `--ioc-format <csv|stix|misp|openioc>`, `--out`.

#### `silentwitness baseline-comparison <case-id>`

Runs the vanilla Protocol SIFT baseline against the same evidence so PRD §4's headline Δ chart is measured, not estimated. Flags: `--baseline <protocol-sift|vanilla>`, `--out`, `--metrics time,pivots,provenance,hallucinations,epistemic`.

#### `silentwitness install --claude-code`

Drop-in: writes `~/.claude/silentwitness.json` + a `.claude/` config bundle so SIFT 2026's pre-installed Claude Code v2.0.61 (`/usr/local/bin/claude`, per `context/.raw-design-research/03`) picks up the MCP server with zero judge setup. Flags: `--claude-code`, `--cursor`, `--continue`, `--dry-run`, `--force`.

#### `silentwitness --version`, `silentwitness --help`

`--version` prints `silentwitness X.Y.Z (mcp X.Y.Z, agent X.Y.Z, model-default <id>)` — bundle provenance for Devpost rules. `--help` per-command; top-level lists the verb grammar.

### 2.3 Live investigation rendering

`silentwitness investigate` renders a four-pane `rich.live.Live` layout at ≤4 Hz (legible over SSH).

```
┌─ silentwitness investigate mr-evil-001 ─────────────────────  12:34:07Z ─┐
│ HYPOTHESIS STACK                                              elapsed 04:32 │
│  H-007 [ACTIVE]    wardriving — Ethereal + intercepted SMTP                │
│  H-006 [ACTIVE]    Schardt is the user (profile Documents and Settings)    │
│  H-005 [CONFIRMED] memory image OS = WinXP SP2                             │
│  H-004 [PIVOTED]   ⤳ vol3 symbol-table mismatch; rebuilt                   │
│  H-003 [CONFIRMED] evidence is single-host disk image                      │
├────────────────────────────────────────────────────────────────────────────┤
│ CURRENT TOOL CALL                                                          │
│   tool:    windows.filescan                                                │
│   target:  Schardt.mem                                                     │
│   audit:   sift-001-20260602-027                                           │
│   elapsed: 00:42  (typical 02:00)                                          │
├────────────────────────────────────────────────────────────────────────────┤
│ FINDINGS                       BUDGET                  LAST EVENT          │
│   staged:    9                  tokens 312k / 800k     12:34:01Z PIVOT     │
│   approved:  0                  steps   47  / 200      H-004 → H-005       │
│   rejected:  1 (entity gate)                            "symbol-table       │
│                                                          rebuilt"          │
└────────────────────────────────────────────────────────────────────────────┘
```

Implementation: `rich.layout.Layout` (4 panes) inside `rich.live.Live`, fed by queues subscribed to `HypothesisEvent` and the MCP audit stream (BRAINSTORM Decision 2). Degrades: no TTY → JSONL `EVT`; `NO_COLOR=1`/`TERM=dumb` → strip ANSI, ASCII box-drawing still aligns; `--quiet` → final status only. Pivots flash yellow for one tick, then settle.

### 2.4 Examiner approval flow

Password-gated HMAC ledger entry. Open Question §8 resolves: **re-prompt every time** (defense — the examiner password is the HMAC key per BRAINSTORM §4; caching defeats the threat model).

Flow:

1. `silentwitness approve F-mr-evil-001-001`
2. Display the finding (observation + interpretation + cited `audit_ids` + caveats + MITRE + confidence)
3. Prompt: `[a]pprove [r]eject [m]odify [s]kip [q]uit`
4. On approve → hidden-input password prompt
5. PBKDF2-SHA256 (600k iter) → HMAC over substantive text → JSONL ledger entry written
6. `report.md` updated by atomic rename; finding promoted to APPROVED
7. Exit 0

```
[green]✓[/green] F-mr-evil-001-001 APPROVED
       ledger:  /var/lib/silentwitness/verification/mr-evil-001.jsonl#14
       hmac:    sha256:b4e1...09cf  (PBKDF2-SHA256, 600,000 iter)
       report.md updated (atomic rename)
```

Edge cases: wrong password → `[red]✗[/red] incorrect (2 attempts remain)`, exit 4 after 3 fails; `[m]odify` → opens `$EDITOR`, edited text is what gets signed; `[r]eject` → prompts for reason, writes signed `REJECTED` ledger entry, unstaged; Ctrl-C → exit 130, no ledger entry.

### 2.5 Error handling + tone

Per §A.7 ("hates slow tools, hates jargon-dense errors"): plain, short, no apology.

**Three-prefix rule** — the *only* emoji in the CLI surface:

- `[green]✓[/green]` — success
- `[yellow]⚠[/yellow]` — warning (operation proceeded)
- `[red]✗[/red]` — error (operation failed)

Errors → stderr. Stdout stays clean for piping.

Citation/entity-gate rejections (PRD §2 demo gold, 3:30–4:00):

```
[red]✗[/red] record_observation REJECTED by entity gate
       reason:   observation contains entities not present in cited spans
       flagged:  "C:\Tools\Ethereal\"   (path not in cited audit_ids)
       cited:    sift-001-20260602-014, sift-001-20260602-019
       hint:     re-read the filescan output; verbatim path may differ
exit code: 3
```

No "Oops!", no "Something went wrong." FOR508 graduates don't need hand-holding.

### 2.6 Configuration

Precedence (lowest → highest): defaults → `~/.silentwitnessrc.toml` → `./.silentwitnessrc.toml` → env vars → CLI flags. CLI wins.

```toml
# ~/.silentwitnessrc.toml
[model]
default = "anthropic:claude-opus-4-7-1m"
critic  = "anthropic:claude-haiku-4-5"

[budget]
max_steps = 200
max_tokens = 800_000

[examiner]
name = "sansforensics"

[hud]
enabled = false
port    = 8088
bind    = "127.0.0.1"

[evidence]
require_ro_mount = true

[output]
color = "auto"      # auto | always | never
emoji = "status"    # status (three indicators) | none
```

Inspect with `silentwitness config --list` (and `--show-origin` to see which layer each value came from — `kubectl` pattern).

---

## 3. Surface 2 — Streaming HUD (optional stretch) — port 8088

### 3.1 Why a HUD

Investigator runs are 5–30 minutes. Per §A.3 the analyst is *always* multi-tasking (customer call, reviewing junior, daily exec update). A HUD on a second monitor lets them keep peripheral eyes on the case while doing other work.

The HUD is a **renderer**, not a control plane. Read-only event stream. Terminal is source-of-truth (Ctrl-C lives there; HUD has no buttons).

Transport: **Server-Sent Events** — one-way push, `curl`-able for debug, survives proxies that mangle WebSocket frames.

### 3.2 Why port 8088

Per `context/.raw-design-research/03 §"Implications" #6`: **Apache binds port 80** on SIFT 2026 to serve CyberChef from `/var/www/html/cyberchef` (verified `scripts/cyberchef.sls:5–24`). 8088 chosen: IANA-unassigned, distinct from common 8080, mnemonic ("two eights" = double witness), above 1024 so no root. Binds `127.0.0.1:8088`; configurable via `[hud].port` and `[hud].bind`.

### 3.3 Visual reference

Anchors: GitHub Actions live-run view (step rail + streaming main pane + status pills); Sentry trace UI (hierarchical events with subtle severity color); Honeycomb traces (high density, no GUI chrome, monospace bias). NOT anchors: Material, Bootstrap, anything with sparklines or pie charts. Forensic tool, not marketing dashboard.

Tailwind **not used**. ≤200 lines of vanilla CSS, inlined (no external CDN — defensive hygiene; `context/.raw-design-research/03 §"Implications" #9` confirms no firewall by default).

### 3.4 Routes

| Route | Purpose |
|---|---|
| `/` | Landing — current case status + last 10 events (server-rendered; JS-free fallback) |
| `/events` | SSE stream — every agent event as `event: <type>\ndata: <json>\n\n` |
| `/case/<case-id>` | Case detail — hypothesis stack, findings, budget; auto-updates from `/events` |
| `/findings` | Staged findings list; click → audit entry deep-link |
| `/audit` | JSONL viewer — paginated with SHA256 column |

No `/approve`, no `/reject`, no write surfaces. Approval lives in CLI per §2.4.

### 3.5 Design tokens (HUD only)

Terminal-inspired dark palette. No bright accents.

| Token | Value |
|---|---|
| Background | `#0a0a0a` |
| Surface | `#1a1a1a` |
| Text primary / secondary | `#e8e8e8` / `#a0a0a0` |
| Success / Warning / Error / Info | `#7fb069` / `#f4a259` / `#d96c5c` / `#5ba3d0` |
| Font | `JetBrains Mono` (bundled WOFF2, base64-inlined; fallback `Menlo, Consolas, monospace`) |
| Border-radius | `2px` — no `rounded-xl` |
| Line-height | `1.5` |

Per Open Question §8: **token spend is shown** in the budget bar (hourly-bill analysts care).

### 3.6 Banned patterns (HUD)

- No Tailwind; vanilla CSS or tiny BEM, ≤200 lines.
- No React/Vue/Svelte/SvelteKit; plain HTML + ≤300 LOC vanilla JS for the SSE subscriber.
- No external CDNs; CSS + font inline.
- No icon fonts; no emoji UI beyond the three status indicators.
- No animation beyond 200ms fade-in on new events (continuity, not flash).
- No charts/sparklines/gauges. Tables and text.
- No login UI — 127.0.0.1 bind only (security by scope, not auth).

### 3.7 Out of scope (HUD v1)

Authentication (loopback bind), multi-case dashboard, persistence, mobile/responsive, light theme.

---

## 4. Demo shape rule

PRD §2's 5-minute video shows a split screen:

```
┌──────────────────────────────────┬──────────────────────────────────┐
│  terminal — silentwitness        │  browser — localhost:8088        │
│  $ silentwitness investigate ... │  [hypothesis stack]              │
│  [live rich layout]              │  [findings · last events]        │
└──────────────────────────────────┴──────────────────────────────────┘
```

Same data, two surfaces. HUD = peripheral glance; terminal = canonical. If they disagree, terminal wins. Judge's eye flows: terminal does the work → HUD makes it watchable → `report.md` is the artifact at the end.

---

## 5. The report — the artifact judges actually read

Per §D.2 and §D.5, the Markdown report is the deliverable. Per PRD §2 (5:00 close), it is what the judge zooms in on.

### 5.1 YAML frontmatter

```yaml
---
case_id: mr-evil-001
examiner: sansforensics
created_at: 2026-06-02T12:00:00Z
updated_at: 2026-06-02T13:48:30Z
status: DRAFT          # DRAFT | REVIEWED | FINAL
content_hash: sha256:f0c2...a991
silentwitness_version: 0.3.1
model_used: anthropic:claude-opus-4-7-1m
---
```

### 5.2 Section skeleton (FOR508-shaped, mapped 1:1 to §D.2)

1. **Executive Summary** — 1 page max; senior's voice; no jargon.
2. **Engagement Overview** — scope, stakeholders, timeline, privilege statement.
3. **Methodology** — tools + versions; evidence inventory with SHA256s; chain of custody; NIST SP 800-86 ref.
4. **Findings** — per host, per TTP. Each: ID, title, severity, confidence, affected systems, description, supporting evidence (inline `[verify:F-id/audit_id]`), MITRE ATT&CK, recommended actions. Matches Mandiant + DFIR Report templates per §D.3.
5. **Timeline of Attack** — table: UTC timestamp, source system, event, audit ref, finding ID.
6. **Indicators of Compromise** — hashes, IPs, domains, regkeys, mutexes; sidecar CSV/STIX/MISP/OpenIOC.
7. **Recommendations** — immediate / short-term / long-term with owner + priority.
8. **Gaps** — Rob T. Lee's epistemic honesty: what we didn't check, hypotheses considered but not pursued.
9. **Appendix-Audit** — JSONL audit-id index with `[verify:]` link resolution.

### 5.3 Inline verify-link rendering

Markdown source:

```markdown
The malware was installed at `C:\Program Files\Ethereal\ethereal.exe`,
evidenced by an MFT record dated 2004-08-19 22:48 UTC
[verify:F-mr-evil-001-001/sift-001-20260602-014].
```

In WeasyPrint PDF: `[verify:...]` renders as superscript link styled `#5ba3d0`, jumping to Appendix-Audit anchored on that `audit_id`. The audit entry shows the JSONL row, SHA256 of the cited tool output, and the verbatim cited span. PRD §2 (4:50–5:00) killer moment.

### 5.4 WeasyPrint stylesheet

Source Serif Pro headings (bundled), JetBrains Mono for evidence/IOCs (same as HUD), single accent `#5ba3d0`. A4 portrait. Page 1 = exec summary; case ID in header. Failure modes from §D.4 mitigated: Appendix-Audit paginated separately (avoids death-by-appendix); tool output lives in audit JSONL only, referenced by ID (no cut-and-paste); finding format enforced by Pydantic schema (no inconsistency); confidence is a required field rendered in a colored pill (no overclaim drift).

### 5.5 Sample 1-page report snippet (Markdown source)

```markdown
---
case_id: mr-evil-001
examiner: sansforensics
status: DRAFT
content_hash: sha256:f0c2a8...a991
---

# Incident Report — Case mr-evil-001

## Executive Summary

Single-host wardriving operation by user "Mr. Evil" (Greg Schardt) on
`SchardtPC`, 2004-08-19 to 2004-08-20. Ethereal (Wireshark) installed
[verify:F-001/sift-001-20260602-014]; intercepted SMTP credentials in
captured pcap [verify:F-003/sift-001-20260602-027]; email
`whoknowsme@sbcglobal.net` registered to same user
[verify:F-004/sift-001-20260602-031]. No second host. No exfil beyond
local pcap.

## Findings (excerpt)

### F-001 — Packet-capture tool present on host
Severity Medium · Confidence Confirmed · MITRE T1040 (Network Sniffing)

Ethereal installed at `C:\Program Files\Ethereal\ethereal.exe`, MFT
record 2004-08-19 22:48:11 UTC
[verify:F-001/sift-001-20260602-014]. Installation alone does not
prove use; corroborated by F-003.

## Gaps
- Wireless-adapter driver state at acquisition not examined.
- Whether intercepted credentials were ever used: not verified.
```

---

## 6. Accessibility + i18n

- **Color-blind safety:** the three status prefixes are distinguished by *shape* (`✓` `⚠` `✗`), not color alone. `NO_COLOR=1` honored.
- **TTY detection:** `sys.stdout.isatty()` everywhere. Non-TTY → plain-text JSONL.
- **Screen-reader:** CLI reads top-to-bottom when piped. HUD uses semantic HTML (`<main>`, `<section>`, `<table>`).
- **Contrast:** HUD `#e8e8e8` on `#0a0a0a` clears WCAG AA at 16px+.
- **i18n:** English only. UTC ISO-8601 throughout. No locale formatting.
- **Keyboard-only:** CLI is keyboard; HUD has no interactions.

---

## 7. Audit against `context/`

- [x] **§B engagement flow** — the CLI verbs map 1:1 onto `§B.1–B.8` (Hours 0–22). We automate `§B.3 / §B.4 / §B.6 / §B.7` which `§B.11` ranks HIGH/HIGH/VERY HIGH/VERY HIGH for AI leverage. Senior keeps `§B.5` containment, `§B.8` briefings, `§B.9` polish — the low-leverage human lanes.
- [x] **§D report anatomy** — our 9-section report (§5.2) is `§D.2` 1:1. The 10 failure modes (§D.4) are mitigated in §5.4. The three handoff tests (§D.5): customer can act (Recommendations); lawyer can defend (Appendix-Audit + chain of custody); executive can decide (1-page Exec Summary).
- [x] **`context/.raw-design-research/03`** — port 80 bound by Apache for CyberChef (`scripts/cyberchef.sls:5–24`); 8088 unbound; JetBrains Mono + Source Serif Pro self-hostable; no Node.js shipped, so HUD is intentionally HTML-only.
- [x] **Template-banned web patterns** (purple gradients, `rounded-xl`, `bg-white`-cards) do not apply to a terminal; HUD section explicitly bans Tailwind, frameworks, CDNs, animation.

---

## 8. Open questions (resolved)

| Question | Resolution |
|---|---|
| `review` — TUI or plain print+prompt? | **Plain print+prompt** for v1. Worst-case user is on flaky `ssh -tt`; plain prompt is robust. Textual is post-hackathon. |
| HUD show LLM token-spend? | **Yes.** Hourly-billing analysts care; budget pane is the natural surface. |
| Examiner password — persist across commands or re-prompt? | **Re-prompt every time.** The password IS the HMAC key (BRAINSTORM §4). Caching defeats the threat model. The friction is the point. |

---

## 9. Spec metadata

- **Status:** DRAFT pending Abu approval.
- **Contributes to:** Usability and Documentation (primary); Audit Trail Quality (report rendering + verify links + Appendix-Audit ARE the audit-trail UX); Autonomous Execution Quality (live hypothesis-stack rendering makes senior-analyst sequencing visible — invisible work doesn't score).
- **Source documents (read in order):** `STRATEGY.md` → `docs/BRAINSTORM.md` → `docs/PRD.md` → `context/user/09-ir-consultant-reality.md` (§A.7, §B, §D) → `context/.raw-design-research/03-sift-2026-tool-catalog-verified.md`.
- **Vocabulary discipline (per PRD §14):** never "court-admissible" → "defensible audit trail" or "survives cross-examination"; never "autonomous SOC" / "replaces L1" / "eliminates hallucinations." CLI copy obeys.
- **Downstream specs:** `docs/architecture.md` (live-pane sources need named event types); `docs/epics.md` (each command = candidate epic); `docs/stories/story-<slug>.md` (BDD acceptance per command + approval flow §2.4 + HUD routes §3.4).

---

**End of UX spec. Awaiting Abu approval.**
