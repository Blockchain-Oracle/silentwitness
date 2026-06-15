"""Section composition helpers for ReportWriter.

Each public function takes pre-loaded data and returns a Markdown body string
(heading excluded — ReportTemplate.render_section adds that). All functions
are deterministic: same inputs → same output for idempotent hash checks.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from silentwitness_agent.report._compose_iocs import compose_iocs

_LOG = logging.getLogger(__name__)

_RECOMMENDATIONS_PLACEHOLDER = "_To be populated by examiner._\n"
_NO_GAPS_PLACEHOLDER = "(no gaps identified)"
_NO_FINDINGS_PLACEHOLDER = "_No findings approved yet._"


_EXEC_SUMMARY_WORD_LIMIT = 500
_TRUNCATION_MARKER = "\n\n[...truncated — see Findings below.]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _unwrap_evidence(text: str) -> str:
    """Strip the sanitizer's ``[UNTRUSTED EVIDENCE BEGIN/END]`` wrap markers for
    display. The markers are a hot-path injection-defense seam, not report prose —
    the examiner-facing report shows the agent's clean interpretation text."""
    cleaned = text.replace("[UNTRUSTED EVIDENCE BEGIN]", "")
    cleaned = cleaned.replace("[UNTRUSTED EVIDENCE END]", "")
    return cleaned.strip()


def _get_interp(obs: dict[str, Any], interp_id: str) -> dict[str, Any] | None:
    """Return the interpretation sub-record matching interp_id from an obs record."""
    for interp in obs.get("interpretations") or []:
        if not isinstance(interp, dict):
            continue
        if interp.get("interpretation_id") == interp_id:
            return interp
    return None


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
            _LOG.warning("Malformed CASE.yaml at %s; using defaults", case_yaml_path, exc_info=True)
        except OSError:
            _LOG.warning(
                "Could not read CASE.yaml at %s; using defaults", case_yaml_path, exc_info=True
            )

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
                        _LOG.debug("Skipping malformed JSON line in %s", jsonl_path)
                        continue
                    if not isinstance(record, dict):
                        continue
                    tool = record.get("tool")
                    if isinstance(tool, str) and tool:
                        tools_seen[tool] = None
            except OSError:
                _LOG.warning("Could not read audit file %s", jsonl_path, exc_info=True)
                continue

    if not tools_seen:
        return "_No tool audit entries recorded._\n"

    tool_lines = "\n".join(f"- `{t}`" for t in tools_seen)
    return f"Tools used during this investigation:\n\n{tool_lines}\n"


def _corroboration_badge(finding: dict[str, Any]) -> str:
    """Tier badge for a finding (empty for legacy/no-tier findings)."""
    tier = finding.get("corroboration_tier")
    if not isinstance(tier, str) or not tier:
        return ""
    cats = finding.get("corroboration_categories")
    suffix = f" · {' + '.join(str(c) for c in cats)}" if isinstance(cats, list) and cats else ""
    return f"**Corroboration:** `{tier}`{suffix}  \n"


def compose_findings(
    approved: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> str:
    """Approved findings + provisional (DRAFT) findings from staged observations.

    The report drafts itself as the case unfolds — examiner-approved findings get
    the signed treatment, observations the agent has staged render as DRAFT so the
    report is never empty mid-investigation. Each approved finding carries a
    `Corroboration:` badge from the materialised tier (Phase 6a); legacy findings
    without the field render unchanged."""
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
        interp_text = _unwrap_evidence(interp.get("text", _no_interp)) if interp else _no_interp
        audit_ids: list[str] = obs.get("audit_ids") or []
        obs_text = obs.get("text", "_No observation text._")

        verify_links = " ".join(f"[verify:{fid}/{aid}]" for aid in audit_ids) if audit_ids else ""
        evidence_line = f"- {obs_text}"
        if verify_links:
            evidence_line += f"  {verify_links}"

        section = (
            f"### {fid} — {title}\n\n"
            f"**Confidence:** {confidence}  \n"
            f"{_corroboration_badge(finding)}"
            f"**Affected systems:** _To be completed by examiner._\n\n"
            f"{interp_text}\n\n"
            f"**Supporting evidence:**\n\n"
            f"{evidence_line}\n\n"
            f"**MITRE ATT&CK:** _To be completed by examiner._  \n"
            f"**Recommended actions:** _See Recommendations section._\n"
        )
        parts.append(section)

    # Provisional (DRAFT) findings — staged observations not yet approved.
    approved_obs = {f.get("observation_id") for f in approved}
    provisional: list[str] = []
    for oid, obs in observations.items():
        if oid in approved_obs:
            continue
        interps = [i for i in (obs.get("interpretations") or []) if isinstance(i, dict)]
        interp = interps[0] if interps else None
        confidence = interp.get("confidence", "MEDIUM") if interp else "—"
        interp_text = (
            _unwrap_evidence(interp["text"])
            if (interp and interp.get("text"))
            else "_No interpretation recorded yet._"
        )
        obs_text = obs.get("text", "_No observation text._")
        obs_audit_ids = obs.get("audit_ids") or []
        verify_links = " ".join(f"[verify:{oid}/{aid}]" for aid in obs_audit_ids)
        evidence_line = f"- {obs_text}" + (f"  {verify_links}" if verify_links else "")
        provisional.append(
            f"### {oid} — provisional (DRAFT)\n\n"
            f"**Confidence:** {confidence}  \n"
            f"**Status:** DRAFT — not yet examiner-approved\n\n"
            f"{interp_text}\n\n"
            f"**Supporting evidence:**\n\n{evidence_line}\n"
        )
    if provisional:
        parts.append(
            "## Provisional findings (DRAFT — pending examiner approval)\n\n"
            + "\n".join(provisional)
        )

    if not parts:
        return _NO_FINDINGS_PLACEHOLDER
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
        rows.append((ts or "—", audit_ref, summary, audit_ref, fid))

    rows.sort(key=lambda r: r[0])

    header = "| Timestamp | Source | Event | Audit Ref | Finding ID |\n"
    sep = "|-----------|--------|-------|-----------|------------|\n"
    body_lines = [
        f"| {ts} | {src} | {event} | {aref} | {fid} |" for ts, src, event, aref, fid in rows
    ]
    return header + sep + "\n".join(body_lines) + "\n"


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
    except json.JSONDecodeError:
        _LOG.error("case_state.json at %s contains invalid JSON", state_path, exc_info=True)
        return _NO_GAPS_PLACEHOLDER
    except OSError:
        _LOG.error("Could not read case_state.json at %s", state_path, exc_info=True)
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


# Sigma detections embed their ATT&CK mapping in the cited evidence text as
# "tags=<tactic>,<techniqueid>" (e.g. "tags=credential_access,t1110"). We derive the
# report's ATT&CK overlay deterministically from those cited tags — no model claim involved.
_ATTACK_TAG_RE = re.compile(r"([a-z_]+),(t\d{4}(?:\.\d{3})?)")


def compose_attack_techniques(case_dir: Path) -> str:
    """Aggregate MITRE ATT&CK techniques from the ATT&CK tags in cited Sigma detections.

    Deterministic: scans each recorded observation's cited ``span_text`` for
    ``<tactic>,<techniqueid>`` tags and renders a technique -> tactic -> evidencing-observation
    table. This is provenance-grounded (it only reports techniques the cited evidence carries),
    not a model assertion."""
    findings_path = case_dir / "findings.json"
    try:
        raw: Any = json.loads(findings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "_No MITRE ATT&CK techniques derived from cited detections._\n"
    if not isinstance(raw, list):
        return "_No MITRE ATT&CK techniques derived from cited detections._\n"

    techniques: dict[str, tuple[str, set[str]]] = {}
    for obs in raw:
        if not isinstance(obs, dict):
            continue
        oid = str(obs.get("observation_id") or obs.get("finding_id") or "?")
        spans = obs.get("cited_spans") or obs.get("cited_span") or []
        for span in spans:
            if not isinstance(span, dict):
                continue
            for tactic, tech in _ATTACK_TAG_RE.findall(str(span.get("span_text", "")).lower()):
                tid = tech.upper()
                techniques.setdefault(tid, (tactic, set()))[1].add(oid)

    if not techniques:
        return "_No MITRE ATT&CK techniques derived from cited detections._\n"
    rows = [
        f"| {tid} | {techniques[tid][0].replace('_', ' ')} | "
        f"{', '.join(sorted(techniques[tid][1]))} |"
        for tid in sorted(techniques)
    ]
    return "| Technique | Tactic | Evidenced by |\n|---|---|---|\n" + "\n".join(rows) + "\n"


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
            _LOG.warning("Could not read audit file %s for digest", path, exc_info=True)
            lines.append(f"- `{path.name}` — _unreadable_")

    return "\n".join(lines) + "\n"


__all__ = [
    "compose_appendix_audit",
    "compose_attack_techniques",
    "compose_engagement_overview",
    "compose_executive_summary",
    "compose_findings",
    "compose_gaps",
    "compose_iocs",
    "compose_methodology",
    "compose_recommendations",
    "compose_timeline",
]
