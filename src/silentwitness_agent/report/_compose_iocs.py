"""IOC extraction + the IOCs report section.

Split out of :mod:`silentwitness_agent.report.compose` to keep each file under
the 400-LOC cap. Re-exported from ``compose`` so callers keep a single import
surface. Deterministic: same inputs -> same output for idempotent hash checks.
"""

from __future__ import annotations

import re
from typing import Any

# IOC patterns — conservative to avoid false positives in prose.
_RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_RE_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
_RE_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
_RE_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_RE_DOMAIN = re.compile(r"\b(?:[a-zA-Z0-9-]{1,63}\.)+(?:com|net|org|io|ru|cn|info|biz|gov|mil)\b")
_RE_REGKEY = re.compile(r"HKEY_[A-Z_]+(?:\\[^\\\"<>\|\n]+)+", re.IGNORECASE)


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


__all__ = ["compose_iocs"]
