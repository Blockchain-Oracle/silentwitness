"""Reader helpers for SilentWitness case directory artifacts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

_AUDIT_SKIP = frozenset(
    {"hypothesis.jsonl", "critic.jsonl", "sanitizer.jsonl", "agent.jsonl", "ledger.jsonl"}
)


def read_findings_json(case_dir: Path) -> list[Any]:
    """Read findings.json; return SwFinding list extracted from finding records."""
    from harness.silentwitness.runner import SwFinding  # lazy: prevents circular import

    path = case_dir / "findings.json"
    if not path.exists():
        return []
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"warning: could not parse {path}: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print(f"warning: {path} contains {type(data).__name__}, expected list", file=sys.stderr)
        return []

    # findings.json has two top-level record types:
    #   - observation records: have "observation_id", no "finding_id"
    #   - finding records:     have both "finding_id" and "observation_id"
    # Build an index of observations only; including finding records would
    # corrupt the index because they share observation_id with their parent.
    obs_index: dict[str, dict[str, Any]] = {
        item["observation_id"]: item
        for item in data
        if isinstance(item, dict) and "observation_id" in item and "finding_id" not in item
    }

    results: list[SwFinding] = []
    for item in data:
        if not isinstance(item, dict) or "finding_id" not in item:
            continue
        obs = obs_index.get(str(item.get("observation_id", "")), {})
        results.append(
            SwFinding(
                id=item["finding_id"],
                observation_id=str(item.get("observation_id", "")),
                interpretation_id=str(item.get("interpretation_id", "")),
                status=str(item.get("status", "DRAFT")),
                title=str(item.get("title", "")),
                cited_audit_ids=list(obs.get("audit_ids", [])),
            )
        )
    return results


def read_hypothesis_jsonl(case_dir: Path) -> tuple[list[Any], list[str]]:
    """Read audit/hypothesis.jsonl; return (SwHypothesisEvent list, skip notes)."""
    from harness.silentwitness.runner import SwHypothesisEvent

    path = case_dir / "audit" / "hypothesis.jsonl"
    if not path.exists():
        return [], []

    results: list[SwHypothesisEvent] = []
    skipped = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(SwHypothesisEvent.model_validate_json(line))
        except (json.JSONDecodeError, ValidationError):
            skipped += 1

    notes = [f"{skipped} malformed hypothesis line(s) skipped."] if skipped else []
    return results, notes


def read_audit_jsonl(case_dir: Path) -> tuple[list[Any], list[str]]:
    """Merge all audit/*.jsonl (except non-tool files); return (tool_calls, notes)."""
    from harness.silentwitness.runner import SwToolCall

    audit_dir = case_dir / "audit"
    if not audit_dir.exists():
        return [], []

    results: list[SwToolCall] = []
    skipped = 0
    for jfile in sorted(audit_dir.glob("*.jsonl")):
        if jfile.name in _AUDIT_SKIP:
            continue
        for raw in jfile.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and "audit_id" in data:
                    results.append(SwToolCall.model_validate(data))
            except (json.JSONDecodeError, ValidationError):
                skipped += 1

    notes = [f"{skipped} malformed audit line(s) skipped."] if skipped else []
    return results, notes


def read_critic_jsonl(case_dir: Path) -> tuple[list[Any], list[str]]:
    """Read audit/critic.jsonl; return (SwCriticVerdict list, skip notes)."""
    from harness.silentwitness.runner import SwCriticVerdict

    path = case_dir / "audit" / "critic.jsonl"
    if not path.exists():
        return [], []

    results: list[SwCriticVerdict] = []
    skipped = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(SwCriticVerdict.model_validate_json(line))
        except (json.JSONDecodeError, ValidationError):
            skipped += 1

    notes = [f"{skipped} malformed critic line(s) skipped."] if skipped else []
    return results, notes


def count_gaps_in_report(report_md_path: Path) -> int:
    """Count '- ' bullet lines under '## Gaps' until the next heading."""
    try:
        content = report_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    m = re.search(r"^## Gaps\b", content, re.MULTILINE)
    if not m:
        return 0
    after = content[m.end() :]
    nxt = re.search(r"^## ", after, re.MULTILINE)
    section = after[: nxt.start()] if nxt else after
    return sum(1 for line in section.splitlines() if line.startswith("- "))


__all__ = [
    "count_gaps_in_report",
    "read_audit_jsonl",
    "read_critic_jsonl",
    "read_findings_json",
    "read_hypothesis_jsonl",
]
