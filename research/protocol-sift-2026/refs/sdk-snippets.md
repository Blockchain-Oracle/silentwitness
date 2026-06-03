# refs/sdk-snippets — MCP Python SDK paste-ready code

Source of truth: `mcp` on PyPI / https://github.com/modelcontextprotocol/python-sdk

---

## 1. Minimal FastMCP server with typed I/O

```python
# server.py
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field
import subprocess
from datetime import datetime, timezone
import json
import hashlib
import secrets
from pathlib import Path

mcp = FastMCP("protocol-sift-v2")

# --- Pydantic models for typed I/O ---

class AmcacheEntry(BaseModel):
    file_name: str = Field(description="Executable name as recorded in Amcache")
    full_path: str
    sha1: str
    file_size: int | None = None
    publisher: str | None = None
    first_run: str | None = Field(default=None, description="ISO 8601 UTC")

class ResponseEnvelope(BaseModel):
    """Valhuntir-style response envelope for every MCP tool call."""
    success: bool
    data: dict
    audit_id: str
    examiner: str
    caveats: list[str] = Field(default_factory=list, description="Forensic caveats — always show")
    advisories: list[str] = Field(default_factory=list, description="Methodology advisories — token-budget decay")
    corroboration: list[str] = Field(default_factory=list, description="Suggested next tools to corroborate")
    discipline_reminder: str | None = None
    data_provenance: str = "tool_output_may_contain_untrusted_evidence"

class AmcacheResult(BaseModel):
    entries: list[AmcacheEntry]
    total: int
    case_id: str

# --- Audit ledger ---

def _record_audit(case_id: str, backend: str, examiner: str, tool: str,
                  params: dict, result_summary: dict, elapsed_ms: float) -> str:
    """Append per-backend JSONL audit entry. Returns stable audit_id."""
    audit_dir = Path(f"/cases/{case_id}/audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_file = audit_dir / f"{backend}.jsonl"

    # Sequence number = count of prior entries today
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    n = 1
    if log_file.exists():
        for line in log_file.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("audit_id", "").endswith(f"-{today}-") or f"-{today}-" in entry.get("audit_id", ""):
                    n += 1
            except json.JSONDecodeError:
                continue

    audit_id = f"{backend}-{examiner}-{today}-{n:03d}"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mcp": backend,
        "tool": tool,
        "audit_id": audit_id,
        "examiner": examiner,
        "case_id": case_id,
        "source": "mcp",
        "params": params,
        "result_summary": result_summary,
        "elapsed_ms": elapsed_ms,
    }
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return audit_id

# --- The tool ---

@mcp.tool()
async def parse_amcache(
    hive_path: str,
    case_id: str,
    examiner: str,
    ctx: Context[ServerSession, None],
) -> ResponseEnvelope:
    """Parse the Amcache.hve hive and return structured execution records.

    Constraints:
    - hive_path MUST be under /evidence/ (read-only mount)
    - Returns typed AmcacheResult, never raw stdout
    - Logs to /cases/{case_id}/audit/sift-mcp.jsonl
    """
    # Architectural guardrail — path validation
    if not hive_path.startswith("/evidence/"):
        raise ValueError(
            f"hive_path must be under /evidence/ (read-only mount). got: {hive_path}"
        )
    if not Path(hive_path).exists():
        raise FileNotFoundError(f"hive not found: {hive_path}")

    await ctx.info(f"Parsing {hive_path}")
    start = datetime.now()

    # Run AmcacheParser — output to a scratch CSV the SERVER parses
    out_dir = Path(f"/tmp/{secrets.token_hex(8)}")
    out_dir.mkdir()
    proc = subprocess.run(
        ["AmcacheParser", "-f", hive_path, "--csv", str(out_dir), "-c", case_id],
        capture_output=True, text=True, timeout=120,
    )
    elapsed_ms = (datetime.now() - start).total_seconds() * 1000

    if proc.returncode != 0:
        # Surface as exception → MCP CallToolResult.isError = true → agent self-corrects
        raise RuntimeError(f"AmcacheParser failed: {proc.stderr[:500]}")

    # Server-side parse (NOT returning raw stdout)
    csv_files = list(out_dir.glob("*.csv"))
    if not csv_files:
        raise RuntimeError("AmcacheParser returned no CSV output")

    entries = _read_amcache_csv(csv_files[0])
    audit_id = _record_audit(
        case_id=case_id, backend="sift-mcp", examiner=examiner,
        tool="parse_amcache",
        params={"hive_path": hive_path, "case_id": case_id},
        result_summary={"entries_count": len(entries), "exit_code": 0},
        elapsed_ms=elapsed_ms,
    )

    return ResponseEnvelope(
        success=True,
        data=AmcacheResult(entries=entries, total=len(entries), case_id=case_id).model_dump(),
        audit_id=audit_id,
        examiner=examiner,
        caveats=[
            "Amcache records file PRESENCE, never execution. Corroborate with Prefetch or Sysmon.",
            "Amcache entries can persist after the file is deleted.",
        ],
        advisories=[
            "Cross-reference SHA1 against known-good baseline (windows-triage-mcp:check_hash).",
        ],
        corroboration=[
            "parse_prefetch — execution evidence",
            "parse_evtx --channel Security --eid 4688 — process creation",
            "windows-triage-mcp:check_hash — baseline lookup",
        ],
        discipline_reminder=(
            "Shimcache and Amcache prove file PRESENCE, never execution. "
            "Always pair with execution evidence (Prefetch, Sysmon EID 1, Security 4688)."
        ),
    )

def _read_amcache_csv(path: Path) -> list[AmcacheEntry]:
    import csv
    entries = []
    with path.open() as f:
        for row in csv.DictReader(f):
            entries.append(AmcacheEntry(
                file_name=row.get("Name", ""),
                full_path=row.get("FullPath", ""),
                sha1=row.get("SHA1", ""),
                file_size=int(row["FileSize"]) if row.get("FileSize") else None,
                publisher=row.get("Publisher"),
                first_run=row.get("KeyLastWriteTimestamp"),
            ))
    return entries

if __name__ == "__main__":
    mcp.run()  # stdio transport
```

Run: `python server.py` and add to your Claude Code config:

```json
{
  "mcpServers": {
    "sift-forensics": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

---

## 2. Long-running operations with progress reporting

```python
@mcp.tool()
async def run_super_timeline(
    image: str,
    case_id: str,
    examiner: str,
    ctx: Context[ServerSession, None],
) -> ResponseEnvelope:
    """Run log2timeline.py against a disk image. Multi-phase, with progress."""
    if not image.startswith("/evidence/"):
        raise ValueError("image must be under /evidence/")

    output = f"/cases/{case_id}/timeline.plaso"

    # Phase 1: parsing
    await ctx.report_progress(progress=0.1, total=1.0, message="log2timeline starting")
    proc = subprocess.Popen(
        ["log2timeline.py", "--quiet", "--storage_file", output, image],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    # Periodic progress reports (could parse log2timeline JSON status if available)
    import asyncio
    while proc.poll() is None:
        await ctx.report_progress(progress=0.5, total=1.0, message="log2timeline running")
        await asyncio.sleep(30)

    if proc.returncode != 0:
        raise RuntimeError(f"log2timeline failed: {proc.stderr.read()[:500].decode()}")

    # Phase 2: psort to CSV
    await ctx.report_progress(progress=0.9, total=1.0, message="psort converting to CSV")
    csv_out = f"/cases/{case_id}/timeline.csv"
    subprocess.run(
        ["psort.py", "-o", "l2tcsv", "-w", csv_out, output],
        check=True, timeout=600,
    )

    await ctx.report_progress(progress=1.0, total=1.0, message="complete")
    # Return only the path + summary, not the multi-million-line CSV
    return ResponseEnvelope(
        success=True,
        data={"plaso_path": output, "csv_path": csv_out, "phase": "complete"},
        # ...
    )
```

---

## 3. Critic subagent pattern (Claude Agent SDK)

This is the **wedge** — closed-loop critic→revise. Uses Claude Agent SDK's subagent primitive.

```python
# critic.py
import json
import os
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()

CRITIC_SYSTEM = """You are a senior forensic peer reviewer. Your job is to challenge findings produced by an autonomous investigator agent.

For each finding bundle you receive, you must:
1. Re-read the cited evidence (via the audit_ids' source files)
2. Check whether the observation matches the evidence
3. Check whether the interpretation is the most parsimonious explanation
4. Check whether confidence is justified by the evidence
5. Identify missing corroboration

Output a structured verdict per finding:
  - AGREE — observation matches evidence, interpretation is sound, confidence appropriate
  - CHALLENGE — observation or interpretation has issues; investigator should revise
  - REJECT — finding is unsupported by the cited evidence and should be removed

You MUST cite the specific evidence (audit_id, file, line, registry key) for any CHALLENGE or REJECT.
You MUST NOT introduce new findings — your role is to validate, not to discover.

You are an adversary to the investigator. Default to skepticism. Better to challenge a correct finding (the investigator can re-justify) than to approve a hallucinated one."""

def critic_review(case_id: str, examiner: str, findings: list[dict]) -> list[dict]:
    """Returns one verdict per finding."""
    verdicts = []
    for f in findings:
        # Re-read the cited audit entries
        evidence = []
        for audit_id in f.get("audit_ids", []):
            entry = _lookup_audit(case_id, audit_id)
            if entry:
                evidence.append(entry)

        if not evidence:
            verdicts.append({
                "finding_id": f["id"],
                "verdict": "REJECT",
                "reason": f"No audit entries found for audit_ids {f.get('audit_ids')}. Provenance: NONE — cannot validate.",
                "suggested_revision": None,
                "missing_corroboration": [],
            })
            _log_critic(case_id, examiner, f["id"], "REJECT", "no audit evidence")
            continue

        # Send finding + evidence to critic LLM
        prompt = f"""<finding>
{json.dumps(f, indent=2)}
</finding>

<evidence>
{json.dumps(evidence, indent=2)}
</evidence>

Produce a JSON verdict matching:
{{
  "finding_id": "<id>",
  "verdict": "AGREE|CHALLENGE|REJECT",
  "reason": "<one paragraph>",
  "suggested_revision": "<if CHALLENGE, what should be revised> | null",
  "missing_corroboration": ["<list of suggested corroborating evidence types>"]
}}"""

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            system=CRITIC_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            verdict = json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            verdict = {
                "finding_id": f["id"],
                "verdict": "CHALLENGE",
                "reason": "Critic returned non-JSON output; defaulting to CHALLENGE.",
                "suggested_revision": "Re-run critic with valid output.",
                "missing_corroboration": [],
            }

        verdicts.append(verdict)
        _log_critic(case_id, examiner, f["id"], verdict["verdict"], verdict["reason"])

    return verdicts

def _lookup_audit(case_id: str, audit_id: str) -> dict | None:
    # audit_id format: {backend}-{examiner}-{YYYYMMDD}-{NNN}
    backend = audit_id.split("-")[0]
    log_file = Path(f"/cases/{case_id}/audit/{backend}.jsonl")
    if not log_file.exists():
        return None
    for line in log_file.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("audit_id") == audit_id:
                return entry
        except json.JSONDecodeError:
            continue
    return None

def _log_critic(case_id: str, examiner: str, finding_id: str, verdict: str, reason: str):
    log_file = Path(f"/cases/{case_id}/audit/critic.jsonl")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "finding_id": finding_id,
        "verdict": verdict,
        "reason": reason,
        "examiner_of_finding": examiner,
    }
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

Wire into the investigation loop:

```python
# After every N findings, fire the critic
if len(staged_findings) % 5 == 0:
    verdicts = critic_review(case_id, examiner, staged_findings[-5:])
    challenges = [v for v in verdicts if v["verdict"] == "CHALLENGE"]
    rejects = [v for v in verdicts if v["verdict"] == "REJECT"]

    # Return CHALLENGE findings to investigator for revision
    if challenges:
        # The main investigator agent now sees the critique in its next turn
        send_to_investigator({"role": "critic", "challenges": challenges})

    # Auto-archive REJECTs
    for r in rejects:
        archive_finding(r["finding_id"], reason=r["reason"])
```

---

## 4. Adversarial-evidence sanitizer

```python
# sanitizer.py
import re
import unicodedata

# Tokens used by major LLMs to delimit roles / instructions
INJECTION_PATTERNS = [
    r"<system>.*?</system>",
    r"<assistant>.*?</assistant>",
    r"<user>.*?</user>",
    r"<\|im_start\|>.*?<\|im_end\|>",
    r"\[INST\].*?\[/INST\]",
    r"### Instruction:.*?(?=### |$)",
    r"###\s*system\s*###.*?(?=###|$)",
    r"Human:.*?(?=\nAssistant:|\Z)",
    r"Assistant:.*?(?=\nHuman:|\Z)",
    r"```ignore previous instructions```",
    r"ignore (?:all |the )?(?:previous|above|prior) (?:instructions|prompts|rules)",
    r"you are (?:now )?(?:in admin|root|developer|debug) mode",
    r"(?:reveal|show|print|output) (?:your |the )?system (?:prompt|instructions)",
]

# Unicode characters used in homoglyph / BIDI attacks
DANGEROUS_UNICODE = [
    "‮",  # RLO (Right-to-Left Override)
    "‭",  # LRO (Left-to-Right Override)
    "​",  # ZWSP (Zero-Width Space)
    "‌",  # ZWNJ
    "‍",  # ZWJ
    "﻿",  # BOM in middle of string
]

def sanitize_evidence_text(raw: str, max_len: int = 5000) -> tuple[str, list[str]]:
    """
    Sanitize a free-text evidence field before sending to LLM.

    Returns (sanitized_text, list_of_flags).

    Flags:
      - "injection_pattern_<n>": a known injection pattern was matched and stripped
      - "dangerous_unicode": homoglyph / BIDI control was removed
      - "truncated": text exceeded max_len
    """
    flags = []
    text = raw

    # Normalize unicode (NFKC collapses fullwidth, etc.)
    text = unicodedata.normalize("NFKC", text)

    # Strip dangerous unicode
    for ch in DANGEROUS_UNICODE:
        if ch in text:
            text = text.replace(ch, "")
            flags.append("dangerous_unicode")

    # Strip injection patterns
    for i, pattern in enumerate(INJECTION_PATTERNS):
        new_text, n = re.subn(pattern, "[STRIPPED]", text, flags=re.IGNORECASE | re.DOTALL)
        if n > 0:
            text = new_text
            flags.append(f"injection_pattern_{i}")

    # Truncate
    if len(text) > max_len:
        text = text[:max_len] + "\n... [TRUNCATED]"
        flags.append("truncated")

    # Wrap in unambiguous untrusted marker
    sanitized = f"[UNTRUSTED EVIDENCE BEGIN]\n{text}\n[UNTRUSTED EVIDENCE END]"
    return sanitized, flags

# Use in MCP tools that return evidence text to the LLM:
@mcp.tool()
async def read_evidence_string(file_path: str, case_id: str, examiner: str,
                                ctx: Context) -> ResponseEnvelope:
    raw = Path(file_path).read_text(errors="replace")
    sanitized, flags = sanitize_evidence_text(raw)
    return ResponseEnvelope(
        success=True,
        data={"text": sanitized, "sanitization_flags": flags, "original_length": len(raw)},
        audit_id=_record_audit(...),
        examiner=examiner,
        caveats=[
            "Evidence text has been sanitized for known prompt-injection patterns.",
            f"Sanitization flags: {flags}" if flags else "No injection patterns detected.",
        ],
        # ...
    )
```

---

## 5. HMAC-signed approval ledger (Valhuntir pattern, paste-ready)

```python
# verification.py
import hashlib
import hmac
import json
import secrets
import os
from pathlib import Path

LEDGER_ROOT = Path("/var/lib/protocol-sift-v2/verification")
PBKDF2_ITERATIONS = 600_000

def derive_hmac_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)

def compute_hmac(derived_key: bytes, description: str) -> str:
    return hmac.new(derived_key, description.encode("utf-8"), hashlib.sha256).hexdigest()

def write_ledger_entry(case_id: str, item_id: str, content_hash: str,
                       hmac_hex: str, examiner: str, item_type: str = "finding"):
    LEDGER_ROOT.mkdir(mode=0o700, exist_ok=True, parents=True)
    log = LEDGER_ROOT / f"{case_id}.jsonl"
    entry = {
        "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "item_id": item_id,
        "item_type": item_type,
        "content_hash": content_hash,
        "hmac": hmac_hex,
        "examiner": examiner,
    }
    with log.open("a") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())
    log.chmod(0o600)

def verify_items(case_id: str, items: list[dict], password: str, salt: bytes) -> list[dict]:
    """Re-derive key, recompute HMACs, constant-time compare. Returns mismatches."""
    derived_key = derive_hmac_key(password, salt)
    log = LEDGER_ROOT / f"{case_id}.jsonl"
    if not log.exists():
        return [{"item_id": i["id"], "verdict": "NO_LEDGER"} for i in items]

    ledger = [json.loads(line) for line in log.read_text().splitlines() if line]
    by_item = {e["item_id"]: e for e in ledger}

    results = []
    for item in items:
        entry = by_item.get(item["id"])
        if not entry:
            results.append({"item_id": item["id"], "verdict": "NOT_IN_LEDGER"})
            continue
        # Reconstruct substantive text the way it was signed
        substantive = item["observation"] + "\n" + item["interpretation"]
        expected_hmac = compute_hmac(derived_key, substantive)
        if hmac.compare_digest(expected_hmac, entry["hmac"]):
            results.append({"item_id": item["id"], "verdict": "VERIFIED"})
        else:
            results.append({
                "item_id": item["id"],
                "verdict": "HMAC_MISMATCH",
                "stale_at_approval": True,
            })
    return results
```

Approval flow:

```python
def approve_finding(case_id: str, finding: dict, examiner: str, password: str):
    # Re-read the staged finding, compute content hash
    substantive = finding["observation"] + "\n" + finding["interpretation"]
    content_hash = hashlib.sha256(substantive.encode("utf-8")).hexdigest()

    # Derive key + HMAC (key never persisted)
    salt = _get_examiner_salt(examiner)  # stored per-examiner at registration
    derived_key = derive_hmac_key(password, salt)
    hmac_hex = compute_hmac(derived_key, substantive)

    # Write to ledger outside the sandbox
    write_ledger_entry(case_id, finding["id"], content_hash, hmac_hex, examiner)

    # Mark finding APPROVED in case state
    finding["status"] = "APPROVED"
    finding["approved_by"] = examiner
    finding["approved_at"] = _now_iso()
    finding["content_hash"] = content_hash
    _save_finding(case_id, finding)
```

---

## 6. Bibliography / further reading

- MCP Python SDK README: https://github.com/modelcontextprotocol/python-sdk
- MCP spec: https://modelcontextprotocol.io/
- Anthropic Agent SDK (Claude Code SDK) docs: https://code.claude.com/docs/en/agent-sdk/overview
- Anthropic "Building agents with the Claude Agent SDK": https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- Valhuntir reference (all patterns above are copied from): https://github.com/AppliedIR/Valhuntir
- AppliedIR/sift-mcp (the actual MCP backend code to mine): https://github.com/AppliedIR/sift-mcp
