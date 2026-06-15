"""Score a live case directory's findings against a dataset's ground truth.

The pre-rearchitecture ``harness/silentwitness/runner.py`` shells out to a CLI signature
that no longer exists (``investigate --evidence --auto-approve``). This adapter scores the
*current* agent output shape directly: it reads ``cases/<id>/findings.json`` (observation
records carrying ``cited_spans`` + ``interpretations``), resolves each cited ``record_id``
to its ``artifact_path`` via the case ``index.db``, and builds the per-finding ``text`` +
``cited_artifact_paths`` the recall scorer matches GT substrings against.

Usage:
    python -m harness.score_case --case cases/rocba --dataset rocba

Exit codes: 0 ok; 2 bad args; 3 missing case/index/findings; 4 empty ground truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Any


def _resolve_paths(case_dir: Path, record_ids: list[int]) -> list[str]:
    """Map index record_ids -> artifact_path strings via the case index (best-effort)."""
    from silentwitness_mcp.index.store import EvidenceIndex

    index_path = case_dir / "index.db"
    paths: list[str] = []
    with EvidenceIndex(index_path) as idx:
        for rid in record_ids:
            rec = idx.get(rid)
            if rec is not None and rec.artifact_path:
                paths.append(rec.artifact_path)
    return paths


def build_findings(case_dir: Path) -> list[dict[str, Any]]:
    """Build scorer-shaped findings from the live findings.json.

    Each observation with cited evidence becomes one scorable finding whose ``text`` is the
    interpretation justifications + the verbatim cited span texts (where the GT substrings —
    OneDrive, Dropbox, RDP, … — actually appear), and whose ``cited_artifact_paths`` are the
    resolved index paths (which carry e.g. the OneDrive/Dropbox path in the filename)."""
    try:
        raw: Any = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    findings: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        spans = item.get("cited_spans") or item.get("cited_span") or []
        spans = [s for s in spans if isinstance(s, dict)]
        record_ids = [int(s["record_id"]) for s in spans if "record_id" in s]
        span_texts = [str(s.get("span_text", "")) for s in spans]
        interps = item.get("interpretations") or []
        justifications = [str(i.get("justification", "")) for i in interps if isinstance(i, dict)]
        text = " ".join([item.get("title", ""), *justifications, *span_texts]).strip()
        if not text and not record_ids:
            continue
        findings.append(
            {
                "id": str(item.get("observation_id", item.get("finding_id", "?"))),
                "text": text,
                "cited_artifact_paths": _resolve_paths(case_dir, record_ids),
            }
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a live case dir against dataset GT.")
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args(argv)

    case_dir: Path = args.case
    if not (case_dir / "findings.json").exists():
        print(f"missing: {case_dir / 'findings.json'}", file=sys.stderr)
        return 3
    if not (case_dir / "index.db").exists():
        print(f"missing: {case_dir / 'index.db'}", file=sys.stderr)
        return 3

    gt_modules = {
        "rocba": "harness.ground_truth.rocba_parser",
        "nitroba": "harness.ground_truth.nitroba_parser",
    }
    if args.dataset not in gt_modules:
        print(f"unknown dataset {args.dataset!r}", file=sys.stderr)
        return 2
    ground_truth = import_module(gt_modules[args.dataset]).parse()
    if not ground_truth:
        print("empty ground truth", file=sys.stderr)
        return 4

    findings = build_findings(case_dir)
    blobs = [f"{f['text']} {' '.join(f['cited_artifact_paths'])}".lower() for f in findings]

    hits: list[Any] = []
    misses: list[Any] = []
    for gt in ground_truth:
        matched = any(
            sub.lower() in blob for blob in blobs for sub in gt.expected_artifact_substrings
        )
        (hits if matched else misses).append(gt)

    total = len(ground_truth)
    print(f"=== {args.dataset} recall: {len(hits)}/{total} = {len(hits) / total:.0%} ===")
    print(f"findings scored: {len(findings)}")
    for gt in ground_truth:
        mark = "HIT " if gt in hits else "MISS"
        print(f"  [{mark}] {gt.id} ({gt.supporting_question_id}) {gt.expected_artifact_substrings}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
