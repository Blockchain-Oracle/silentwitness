# refs/sponsor-repos — Sponsor & reference repos with clone commands

Every repo we care about, with clone commands and what to borrow.

---

## Core sponsor repos

### 1. teamdfir/protocol-sift (the baseline — extend this)

```bash
git clone --depth 1 https://github.com/teamdfir/protocol-sift /tmp/protocol-sift
```

**Why clone:** Read the 5 SKILL.md files for the SIFT tool invocations the sponsor has already pre-approved. Borrow the deny list (`global/settings.json` line ~100). Borrow the case-template `CLAUDE.md` structure.

**Do NOT borrow:** the install pattern (prompt-only guardrails, no MCP). We replace this layer.

---

### 2. AppliedIR/Valhuntir (the bar — study but don't fork)

```bash
git clone --depth 1 https://github.com/AppliedIR/Valhuntir /tmp/valhuntir
```

**Why clone:** Read `docs/architecture.md`, `docs/security.md`, `docs/clients.md`. Read `src/vhir_cli/verification.py` for the HMAC ledger pattern (paste-ready in `refs/sdk-snippets.md` §5). Read `src/vhir_cli/commands/approve.py` for the approval flow.

**Borrow patterns:**
- Response envelope shape
- Finding schema (`F-<examiner>-<NNN>` IDs)
- Audit JSONL schema + stable `audit_id` format
- HMAC ledger pattern (PBKDF2 600K iters, HMAC-SHA256, mode 0600, fsync)
- Provenance tier classification
- 41-rule Claude Code deny list (`.claude/settings.json`)
- 6 report profiles

**Do NOT borrow:**
- The CLI itself (build our own)
- The 11-package monorepo split (overkill for 13 days)
- Examiner Portal as built (we can build a simpler streaming HUD)

---

### 3. AppliedIR/sift-mcp (the MCP backend code — mine this)

```bash
git clone --depth 1 https://github.com/AppliedIR/sift-mcp /tmp/sift-mcp
```

**Why clone:** This is where the actual MCP server code lives. 11 packages. Read:
- `packages/forensic-mcp` for the investigation state machine + 14 discipline tools
- `packages/sift-mcp` for the tool execution pattern (`run_command` + denylist)
- `packages/forensic-rag-mcp` for the semantic search pattern
- `packages/case-mcp` for case lifecycle

**Borrow patterns:**
- Per-backend stdio MCP server structure
- Forensic Knowledge (FK) YAML format for per-tool contexts
- Token-budget decay for advisory injection
- MCP Resources vs Tools split for static discipline content

---

### 4. AppliedIR/wintools-mcp (Windows MCP pattern)

```bash
git clone --depth 1 https://github.com/AppliedIR/wintools-mcp /tmp/wintools-mcp
```

**Why clone:** If we add Windows-side tool execution. 10 tools, 31 catalog entries, hardcoded denylist of 20+ binaries.

**Borrow:** Argument sanitization pattern (blocks shell metacharacters, `@filename` response-file syntax, `-e/-enc` flags).

---

### 5. AppliedIR/opensearch-mcp (evidence indexing pattern)

```bash
git clone --depth 1 https://github.com/AppliedIR/opensearch-mcp /tmp/opensearch-mcp
```

**Why clone:** 15 parsers (evtx, EZ Tools CSV, Volatility 3 JSON, JSONL, delimited, W3C access logs, MPLog, schtasks, WER, SSH, PowerShell transcripts, Prefetch/SRUM, Hayabusa CSV). If we need any of those parsers, borrow rather than rewrite.

**Borrow:** Deterministic content-based document IDs (re-ingest = 0 dupes). Hayabusa auto-run pattern post-evtx-ingest.

**Do NOT borrow:** OpenSearch dependency (too heavy for 13 days; SQLite or DuckDB is sufficient for our scale).

---

### 6. sans-dfir/sift (the platform — for reference)

Don't clone (OVA is GB). Read the README:
```bash
curl -sL https://raw.githubusercontent.com/sans-dfir/sift/main/README.md
```

**Why care:** SIFT install instructions, base distro, supported VM platforms. Most actual work happens in `teamdfir/sift-saltstack` (below).

---

### 7. teamdfir/sift-saltstack (the install)

```bash
git clone --depth 1 https://github.com/teamdfir/sift-saltstack /tmp/sift-saltstack
```

**Why clone:** Authoritative list of tools installed on SIFT. Salt states map directly to packages. Useful for figuring out which tools are guaranteed present.

---

## MCP framework repos

### 8. modelcontextprotocol/python-sdk

```bash
git clone --depth 1 https://github.com/modelcontextprotocol/python-sdk /tmp/mcp-python
```

**Why clone:** The MCP Python SDK. Read `examples/` for canonical FastMCP usage patterns. Read `src/mcp/server/fastmcp/` for the decorator implementation.

---

### 9. anthropics/claude-agent-sdk-python

```bash
git clone --depth 1 https://github.com/anthropics/claude-agent-sdk-python /tmp/agent-sdk
```

**Why clone:** Claude Agent SDK (formerly Claude Code SDK). Subagents, hooks, MCP integration. Read `examples/` for the subagent pattern (used in our critic agent).

---

## Existing MCP forensics servers (DO NOT duplicate — read for diff)

### 10. bornpresident/Volatility-MCP-Server

```bash
git clone --depth 1 https://github.com/bornpresident/Volatility-MCP-Server /tmp/vol-mcp-other
```

**Why clone:** 14 Volatility plugins exposed via MCP. If we build the memory-first investigator wedge, we should know what this MCP does so we go beyond plain plugin exposure.

---

### 11. socfortress/velociraptor-mcp-server

```bash
git clone --depth 1 https://github.com/socfortress/velociraptor-mcp-server /tmp/velo-mcp
```

**Why clone:** 11 Velociraptor tools (Auth, GetAgentInfo, ListArtifacts, CollectArtifact, CollectArtifactDetails, FindArtifactDetails, GetCollectionResults, RunVQLQuery). JWT auth, retry logic. If we go for the live-host triage wedge, BUILD ON TOP of this rather than duplicating it.

---

### 12. mgreen27/mcp-velociraptor

```bash
git clone --depth 1 https://github.com/mgreen27/mcp-velociraptor /tmp/velo-mcp-alt
```

**Why clone:** Alternative Velociraptor MCP bridge. Compare to socfortress's to pick the cleaner base.

---

## Volatility & forensic tools

### 13. volatilityfoundation/volatility3

```bash
git clone --depth 1 https://github.com/volatilityfoundation/volatility3 /tmp/vol3
```

**Why clone:** The actual Vol3 source. Read `volatility3/framework/plugins/windows/*.py` to understand what each plugin produces. We need this for our memory-first investigator wedge.

---

### 14. log2timeline/plaso

```bash
git clone --depth 1 https://github.com/log2timeline/plaso /tmp/plaso
```

**Why clone:** plaso source. Read `plaso/parsers/` to know which forensic artifacts are auto-parsed (~270 parsers). Useful for the super-timeline tool.

---

### 15. EricZimmerman tools

EZ Tools are .NET single-file binaries. **No GitHub clone needed.** Download from:
- https://ericzimmerman.github.io/
- Tools list: MFTECmd, EvtxECmd, AmcacheParser, AppCompatCacheParser, PECmd, RECmd, RBCmd, SBECmd, LECmd, JLECmd, SrumECmd, SQLECmd, bstrings, WxTCmd

Run natively on Linux per the SANS guide: https://www.sans.org/blog/running-ez-tools-natively-on-linux-a-step-by-step-guide

---

### 16. Yamato-Security/hayabusa

```bash
git clone --depth 1 https://github.com/Yamato-Security/hayabusa /tmp/hayabusa
```

**Why clone:** Rust-based Sigma rule engine. 4000+ rules. Fast. We'll likely call it via subprocess, not extend it.

---

### 17. WithSecureLabs/chainsaw

```bash
git clone --depth 1 https://github.com/WithSecureLabs/chainsaw /tmp/chainsaw
```

**Why clone:** Alternative to Hayabusa. Same domain (Sigma + EVTX). Different output format. Keep as fallback.

---

### 18. SigmaHQ/sigma

```bash
git clone --depth 1 https://github.com/SigmaHQ/sigma /tmp/sigma
```

**Why clone:** The Sigma rule corpus. If we build the YARA-rule-generation wedge variant, we may want to emit Sigma rules from observed log patterns.

---

### 19. keydet89/RegRipper3.0

```bash
git clone --depth 1 https://github.com/keydet89/RegRipper3.0 /tmp/regripper
```

**Why clone:** Hive-specific Perl plugins (300+). Source-of-truth for which registry keys to query. If we wrap RegRipper in an MCP tool, we need to know which plugins map to which artifacts.

---

## MITRE / threat intel

### 20. mitre/cti

```bash
git clone --depth 1 https://github.com/mitre/cti /tmp/mitre-cti
```

**Why clone:** Authoritative MITRE ATT&CK content in STIX format. Use for tagging findings with technique IDs and pulling descriptions.

---

## Public competitor build

### 21. marez8505/find-evil

```bash
git clone --depth 1 https://github.com/marez8505/find-evil /tmp/marez
```

**Why clone:** A real public hackathon submission. 1 star, MIT, 5-phase pipeline w/ Flask UI. Read to understand the solo-builder shape we're competing against.

---

## Quick batch-clone script

```bash
#!/bin/bash
# clone-all-research-repos.sh
set -e
mkdir -p /tmp/find-evil-research
cd /tmp/find-evil-research

repos=(
  "teamdfir/protocol-sift"
  "AppliedIR/Valhuntir"
  "AppliedIR/sift-mcp"
  "AppliedIR/wintools-mcp"
  "AppliedIR/opensearch-mcp"
  "teamdfir/sift-saltstack"
  "modelcontextprotocol/python-sdk"
  "anthropics/claude-agent-sdk-python"
  "bornpresident/Volatility-MCP-Server"
  "socfortress/velociraptor-mcp-server"
  "volatilityfoundation/volatility3"
  "log2timeline/plaso"
  "Yamato-Security/hayabusa"
  "WithSecureLabs/chainsaw"
  "SigmaHQ/sigma"
  "keydet89/RegRipper3.0"
  "mitre/cti"
  "marez8505/find-evil"
)

for r in "${repos[@]}"; do
  name="$(echo "$r" | cut -d/ -f2)"
  if [ ! -d "$name" ]; then
    git clone --depth 1 "https://github.com/$r"
  fi
done
echo "✅ All research repos cloned to /tmp/find-evil-research/"
```
