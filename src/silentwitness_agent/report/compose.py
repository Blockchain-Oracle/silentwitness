"""Section composition helpers for ReportWriter.

Each public function takes pre-loaded data and returns a Markdown body string
(heading excluded — ReportTemplate.render_section adds that). All functions
are deterministic: same inputs → same output for idempotent hash checks.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

_RECOMMENDATIONS_PLACEHOLDER = "_To be populated by examiner._\n"
_NO_GAPS_PLACEHOLDER = "(no gaps identified)"
_NO_FINDINGS_PLACEHOLDER = "_No findings approved yet._"

# IOC patterns — conservative to avoid false positives in prose
_RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_RE_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
_RE_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
_RE_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_RE_DOMAIN = re.compile(r"\b(?:[a-zA-Z0-9-]{1,63}\.)+(?:com|net|org|io|ru|cn|info|biz|gov|mil)\b")
_RE_REGKEY = re.compile(r"HKEY_[A-Z_]+(?:\\[^\\\"<>\|\n]+)+", re.IGNORECASE)

_EXEC_SUMMARY_WORD_LIMIT = 500
_TRUNCATION_MARKER = "\n\n[...truncated — see Findings below.]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_interp(obs: dict[str, Any], interp_id: str) -> dict[str, Any] | None:
    """Return the interpretation sub-record matching interp_id from an obs record."""
    for interp in obs.get("interpretations") or []:
        if not isinstance(interp, dict):
            continue
        if interp.get("interpretation_id") == interp_id:
            return interp
    return None


def _extract_iocs(text: str) -> dict[str, list[str]]:
    """Extract IOC candidates from observation text grouped by type."""
    result: dict[str, list[str]] = {}

    def _add(key: str, matches: list[str]) -> None:
        unique = list(dict.fromkeys(matches))
        if unique:
            result[key] = unique

    # Order matters: try longest patterns first to avoid partial matches
    sha256_matches = _RE_SHA256.findall(text)
    sha1_matches = [m for m in _RE_SHA1.findall(text) if m not in sha256_matches]
    md5_matches = [
        m for m in _RE_MD5.findall(text) if m not in sha256_matches and m not in sha1_matches
    ]

    _add("SHA-256", sha256_matches)
    _add("SHA-1", sha1_matches)
    _add("MD5", md5_matches)
    _add("IP", _RE_IPV4.findall(text))
    _add("Domain", _RE_DOMAIN.findall(text))
    _add("RegistryKey", _RE_REGKEY.findall(text))

    return result


# ---------------------------------------------------------------------------
# Public compose functions
# ---------------------------------------------------------------------------


def compose_executive_summary(
    approved: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> str:
    """≤500-word auto-summary from approved interpretation texts."""
    if not approved:
        return _NO_FINDINGS_PLACEHOLDER

    lines: list[str] = []
    for finding in approved:
        fid = finding.get("finding_id", "")
        obs_id = finding.get("observation_id", "")
        interp_id = finding.get("interpretation_id", "")
        obs = observations.get(obs_id, {})
        interp = _get_interp(obs, interp_id)
        if not interp:
            continue
        text = interp.get("text", "").strip()
        if not text:
            continue
        # Use first sentence only for the summary
        first_sentence = re.split(r"(?<=[.!?])\s", text)[0]
        confidence = interp.get("confidence", "MEDIUM")
        lines.append(f"- **{fid}** [{confidence}]: {first_sentence}")

    if not lines:
        return _NO_FINDINGS_PLACEHOLDER

    body = "\n".join(lines)
    words = body.split()
    if len(words) <= _EXEC_SUMMARY_WORD_LIMIT:
        return body

    truncated = " ".join(words[:_EXEC_SUMMARY_WORD_LIMIT])
    # Trim to last sentence boundary
    last_boundary = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))
    if last_boundary > 0:
        truncated = truncated[: last_boundary + 1]
    return truncated + _TRUNCATION_MARKER


def compose_engagement_overview(case_dir: Path, case_id: str, examiner: str) -> str:
    """Auto-composed from CASE.yaml metadata with privilege placeholder."""
    case_yaml_path = case_dir / "CASE.yaml"
    case_meta: dict[str, Any] = {}
    if case_yaml_path.exists():
        try:
            loaded = yaml.safe_load(case_yaml_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                case_meta = loaded
        except yaml.YAMLError:
            pass

    start_date = case_meta.get("start_date", "_not recorded_")
    scope = case_meta.get("scope", "_not recorded_")

    return (
        f"**Case ID:** {case_id}  \n"
        f"**Examiner:** {examiner}  \n"
        f"**Start date:** {start_date}  \n"
        f"**Scope:** {scope}  \n"
        f"**Access level:** _To be completed by examiner._\n"
    )


def compose_methodology(case_dir: Path) -> str:
    """Lists unique tools observed across all audit/*.jsonl files."""
    audit_dir = case_dir / "audit"
    tools_seen: dict[str, None] = {}  # ordered set via insertion-order dict
    if audit_dir.exists():
        for jsonl_path in sorted(audit_dir.glob("*.jsonl")):
            try:
                for line in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(record, dict):
                        continue
                    tool = record.get("tool")
                    if isinstance(tool, str) and tool:
                        tools_seen[tool] = None
            except OSError:
                continue

    if not tools_seen:
        return "_No tool audit entries recorded._\n"

    tool_lines = "\n".join(f"- `{t}`" for t in tools_seen)
    return f"Tools used during this investigation:\n\n{tool_lines}\n"


def compose_findings(
    approved: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> str:
    """Per-finding subsections with inline [verify:F-id/audit_id] references."""
    if not approved:
        return _NO_FINDINGS_PLACEHOLDER

    parts: list[str] = []
    for finding in approved:
        fid = finding.get("finding_id", "F-???")
        obs_id = finding.get("observation_id", "")
        interp_id = finding.get("interpretation_id", "")
        title = finding.get("title") or fid
        obs = observations.get(obs_id, {})
        interp = _get_interp(obs, interp_id)
        confidence = interp.get("confidence", "MEDIUM") if interp else "MEDIUM"
        _no_interp = "_No interpretation recorded._"
        interp_text = interp.get("text", _no_interp) if interp else _no_interp
        audit_ids: list[str] = obs.get("audit_ids") or []
        obs_text = obs.get("text", "_No observation text._")

        verify_links = " ".join(f"[verify:{fid}/{aid}]" for aid in audit_ids) if audit_ids else ""
        evidence_line = f"- {obs_text}"
        if verify_links:
            evidence_line += f"  {verify_links}"

        section = (
            f"### {fid} — {title}\n\n"
            f"**Confidence:** {confidence}  \n"
            f"**Affected systems:** _To be completed by examiner._\n\n"
            f"{interp_text}\n\n"
            f"**Supporting evidence:**\n\n"
            f"{evidence_line}\n\n"
            f"**MITRE ATT&CK:** _To be completed by examiner._  \n"
            f"**Recommended actions:** _See Recommendations section._\n"
        )
        parts.append(section)

    return "\n".join(parts)


def compose_timeline(
    approved: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> str:
    """Chronological table sorted by interpretation recorded_at."""
    if not approved:
        return "_No approved findings to render in timeline._\n"

    rows: list[tuple[str, str, str, str, str]] = []
    for finding in approved:
        fid = finding.get("finding_id", "F-???")
        obs_id = finding.get("observation_id", "")
        interp_id = finding.get("interpretation_id", "")
        obs = observations.get(obs_id, {})
        interp = _get_interp(obs, interp_id)
        ts = (interp.get("recorded_at") or "") if interp else ""
        audit_ids: list[str] = obs.get("audit_ids") or []
        audit_ref = audit_ids[0] if audit_ids else "—"
        obs_text = obs.get("text", "—")
        summary = obs_text[:80] + "…" if len(obs_text) > 80 else obs_text
        source = audit_ref.split("-")[1] if "-" in audit_ref else "—"
        rows.append((ts or "—", source, summary, audit_ref, fid))

    rows.sort(key=lambda r: r[0])

    header = "| Timestamp | Source | Event | Audit Ref | Finding ID |\n"
    sep = "|-----------|--------|-------|-----------|------------|\n"
    body_lines = [
        f"| {ts} | {src} | {event} | {aref} | {fid} |" for ts, src, event, aref, fid in rows
    ]
    return header + sep + "\n".join(body_lines) + "\n"


def compose_iocs(
    approved: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> str:
    """Groups IOC candidates by type with audit_id citations."""
    if not approved:
        return "_No approved findings to extract IOCs from._\n"

    # {ioc_type: {ioc_value: [audit_id, ...]}}
    grouped: dict[str, dict[str, list[str]]] = {}

    for finding in approved:
        obs_id = finding.get("observation_id", "")
        obs = observations.get(obs_id, {})
        text = obs.get("text", "")
        audit_ids: list[str] = obs.get("audit_ids") or []
        if not text:
            continue
        for ioc_type, values in _extract_iocs(text).items():
            bucket = grouped.setdefault(ioc_type, {})
            for val in values:
                bucket.setdefault(val, []).extend(audit_ids)

    if not grouped:
        return "_No IOC candidates extracted from approved findings._\n"

    parts: list[str] = []
    for ioc_type in sorted(grouped):
        parts.append(f"**{ioc_type}**\n")
        for val, aids in sorted(grouped[ioc_type].items()):
            # Deduplicate audit_ids while preserving order
            seen: dict[str, None] = {}
            for a in aids:
                seen[a] = None
            citations = " ".join(f"[{a}]" for a in seen)
            parts.append(f"- `{val}` — {citations}\n")

    return "\n".join(parts)


def compose_recommendations() -> str:
    """Returns the examiner-only placeholder (agent must not write here)."""
    return _RECOMMENDATIONS_PLACEHOLDER


def compose_gaps(case_dir: Path) -> str:
    """Reads case_state.json for gap items; falls back to '(no gaps identified)'."""
    state_path = case_dir / "case_state.json"
    if not state_path.exists():
        return _NO_GAPS_PLACEHOLDER

    try:
        state: Any = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _NO_GAPS_PLACEHOLDER

    if not isinstance(state, dict):
        return _NO_GAPS_PLACEHOLDER

    items: list[str] = []
    for key in ("abandoned_hypotheses", "exhausted_budgets", "explicit_gaps"):
        for entry in state.get(key) or []:
            if isinstance(entry, str) and entry.strip():
                items.append(entry.strip())
            elif isinstance(entry, dict):
                label = entry.get("label") or entry.get("id") or str(entry)
                items.append(str(label).strip())

    if not items:
        return _NO_GAPS_PLACEHOLDER

    return "\n".join(f"- {item}" for item in items) + "\n"


def compose_appendix_audit(case_dir: Path) -> str:
    """Lists each audit/*.jsonl with its SHA-256 digest."""
    audit_dir = case_dir / "audit"
    if not audit_dir.exists():
        return "_No audit logs found._\n"

    jsonl_files = sorted(audit_dir.glob("*.jsonl"))
    if not jsonl_files:
        return "_No audit logs found._\n"

    lines: list[str] = []
    for path in jsonl_files:
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rel = path.relative_to(case_dir)
            lines.append(f"- `{rel}` — `sha256:{digest}`")
        except OSError:
            lines.append(f"- `{path.name}` — _unreadable_")

    return "\n".join(lines) + "\n"


__all__ = [
    "compose_appendix_audit",
    "compose_engagement_overview",
    "compose_executive_summary",
    "compose_findings",
    "compose_gaps",
    "compose_iocs",
    "compose_methodology",
    "compose_recommendations",
    "compose_timeline",
]
