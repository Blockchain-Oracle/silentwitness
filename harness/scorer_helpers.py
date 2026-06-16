"""Internal helpers for harness/scorer.py (split to stay under 400-LOC gate)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from harness.scorer_models import (
    FindingClassification,
    HallucinationExample,
    ScoringMetrics,
)


def get_commit_sha() -> str:
    """Return HEAD SHA or an `unknown (...)` sentinel describing the failure."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        return r.stdout.strip() if r.returncode == 0 else f"unknown (git exit {r.returncode})"
    except FileNotFoundError:
        return "unknown (git not found on PATH)"
    except subprocess.TimeoutExpired:
        return "unknown (git rev-parse timed out)"
    except (subprocess.SubprocessError, OSError) as exc:
        return f"unknown ({type(exc).__name__}: {exc})"


def check_mount_writable(evidence_root: Path, notes: list[str]) -> None:
    """Append a note if evidence_root is writable or statvfs fails."""
    try:
        flags = os.statvfs(str(evidence_root)).f_flag
        if not (flags & os.ST_RDONLY):
            notes.append(
                f"warning: evidence mount at {evidence_root} appears writable "
                "(expected ro,noexec,nosuid; proceeding)"
            )
    except OSError as exc:
        notes.append(f"warning: could not statvfs evidence mount {evidence_root}: {exc}")


def safe_findings(raw: object, notes: list[str], side: str) -> list[dict[str, Any]]:
    """Validate findings input shape; drop and note malformed entries."""
    if not isinstance(raw, list):
        notes.append(f"warning: {side} findings is not a list ({type(raw).__name__}); dropping")
        return []
    out: list[dict[str, Any]] = []
    for i, f in enumerate(raw):
        if not isinstance(f, dict):
            notes.append(f"warning: {side} findings[{i}] is not a dict; skipped")
            continue
        cited = f.get("cited_artifact_paths", [])
        if not isinstance(cited, list) or not all(isinstance(c, str) for c in cited):
            notes.append(f"warning: {side} findings[{i}].cited_artifact_paths != list[str]")
            f = {**f, "cited_artifact_paths": []}
        out.append(f)
    return out


def mk_classification(
    finding_id: str, side: str, classification: str, reason: str, **kw: Any
) -> FindingClassification:
    """Build a FindingClassification with sensible defaults for unused fields."""
    return FindingClassification(
        finding_id=finding_id,
        side=side,  # type: ignore[arg-type]
        classification=classification,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        matched_ground_truth_id=kw.get("matched_ground_truth_id"),
        evidence_shellout_argv=kw.get("evidence_shellout_argv"),
        evidence_shellout_hits=kw.get("evidence_shellout_hits", 0),
        notes=kw.get("notes", []),
    )


def cited_from_argv(argv: list[str]) -> str:
    """Recover the cited substring from a verify_artifact_present_in_evidence argv."""
    if not argv:
        return ""
    if argv[0] == "find" and len(argv) >= 4:
        return argv[3]
    if argv[0] == "grep" and len(argv) >= 2:
        return argv[-2]
    return argv[-1]


def build_metrics(
    dataset_id: str,
    side: str,
    classifications: list[FindingClassification],
    fn_count: int,
    result: dict[str, Any],
    total_findings: int,
) -> ScoringMetrics:
    """Aggregate per-side counts into ScoringMetrics + pass through timing fields."""
    tp = sum(1 for c in classifications if c.classification == "TRUE_POSITIVE")
    fp = sum(1 for c in classifications if c.classification == "FALSE_POSITIVE")
    hall = sum(1 for c in classifications if c.classification == "HALLUCINATION")
    return ScoringMetrics(
        dataset_id=dataset_id,
        side=side,  # type: ignore[arg-type]
        true_positives=tp,
        false_positives=fp,
        hallucinations=hall,
        false_negatives=fn_count,
        total_findings_emitted=total_findings,
        time_to_first_finding_seconds=result.get("time_to_first_finding_seconds"),
        time_to_handoff_ready_report_seconds=result.get("time_to_handoff_ready_report_seconds"),
    )


def top_hallucination_examples(
    classifications: list[FindingClassification], side: str
) -> list[HallucinationExample]:
    """Sort hallucinations by cited-substring length and surface top 10 as examples."""
    halls = [
        c
        for c in classifications
        if c.classification == "HALLUCINATION" and c.evidence_shellout_argv is not None
    ]
    halls.sort(key=lambda c: len(cited_from_argv(c.evidence_shellout_argv or [])), reverse=True)
    examples = []
    for c in halls[:10]:
        argv = c.evidence_shellout_argv or []
        cited = cited_from_argv(argv)
        examples.append(
            HallucinationExample(
                side=side,  # type: ignore[arg-type]
                finding_id=c.finding_id,
                cited_artifact_path=cited,
                evidence_shellout_argv=argv,
                evidence_shellout_hits=c.evidence_shellout_hits or 0,
                excerpt=cited[:200],
            )
        )
    return examples
